"""种子词库导入测试。

词库是整个产品的输入源：词错了，判题、统计、复习计划会一起错，
而且错得很隐蔽（家长会以为是孩子记不住）。

所以这里不只测「能导入」，还测：
- 重复导入不会产生重复词条（幂等）
- 写错的行会被报出来，而不是被静默丢弃
- 一个单词的多个义项会被分开保存（判题要按义项记账）
- accepted 同义写法被正确解析成列表
- 空跑报出的数字与真实导入完全一致（否则 --dry-run 是个假保险）
"""
import pytest
from sqlalchemy import func

from core.models import Book, Unit, Word, WordSense
from tools.load_seed import (
    DEFAULT_UNITS_CSV,
    DEFAULT_WORDS_CSV,
    import_seed,
    load_units,
    load_words,
    main,
    read_csv,
)

WORDS_HEADER = "unit_code,spelling,pos,phonetic_uk,phonetic_us,sense_order,meaning_zh,accepted,theme,example_en,example_zh,source,source_license,verify_status"


def load_all(session, words_csv=DEFAULT_WORDS_CSV, term="上册"):
    unit_index, unit_stats = load_units(session, read_csv(DEFAULT_UNITS_CSV))
    word_stats = load_words(session, read_csv(words_csv), unit_index, term)
    return unit_stats, word_stats


def test_seed_loads_books_and_units(seeded_db):
    with seeded_db.session() as s:
        assert s.query(Book).count() == 2  # 七上 / 七下
        assert s.query(Unit).count() == 18  # 上 10 + 下 8


def test_seed_loads_words_and_senses(seeded_db):
    with seeded_db.session() as s:
        assert s.query(Word).count() == 50
        assert s.query(WordSense).count() == 52  # 50 个词 + 2 个第二义项


def test_seed_unit_word_counts(seeded_db):
    """单元词数必须由数据算出来，这是「胶囊写 20、实际 13」那个 bug 的解药。

    注意必须同时按册别过滤：上下册都有 U01/U02，只按 unit_code 查会查出两行。
    """
    expected = {"SU01": 10, "SU02": 16, "SU03": 8, "U01": 10, "U02": 6}
    with seeded_db.session() as s:
        for code, count in expected.items():
            unit = (
                s.query(Unit)
                .join(Book, Book.id == Unit.book_id)
                .filter(Unit.unit_code == code, Book.term == "上册")
                .one()
            )
            actual = s.query(func.count(Word.id)).filter(Word.unit_id == unit.id).scalar()
            assert actual == count, f"{code} 期望 {count} 词，实际 {actual}"


def test_reload_is_idempotent(seeded_db):
    """再导一次不应该新增任何词条 —— 这是可以放心重跑的前提。"""
    with seeded_db.session() as s:
        _, stats = load_all(s)
        assert stats.words_created == 0
        assert stats.senses_created == 0
        assert s.query(Word).count() == 50
        assert s.query(WordSense).count() == 52


def test_multi_sense_word_kept_separate(seeded_db):
    with seeded_db.session() as s:
        word = s.query(Word).filter_by(spelling="class").one()
        meanings = [sense.meaning_zh for sense in word.senses]
        assert meanings == ["班级", "课"]


def test_accepted_variants_parsed(seeded_db):
    with seeded_db.session() as s:
        sense = s.query(WordSense).filter(WordSense.meaning_zh == "爷爷").one()
        assert sense.accepted == ["祖父", "外公", "姥爷"]


def test_duplicate_row_in_csv_reported(db, tmp_path):
    """同一个 CSV 里重复写同一个义项，应报错而不是悄悄合并。

    重复行的危险在于：两行内容可能不同（比如改了一半忘了删旧行），
    静默合并等于让「最后一行」随机胜出，谁也不知道最终生效的是哪一条。
    """
    bad = tmp_path / "dup.csv"
    bad.write_text(
        WORDS_HEADER
        + "\nSU01,apple,n.,/x/, ,1,苹果,,物品,,,,,pending"
        + "\nSU01,apple,n.,/x/, ,1,苹果,,物品,,,,,pending\n",
        encoding="utf-8",
    )
    with db.session() as s:
        unit_index, _ = load_units(s, read_csv(DEFAULT_UNITS_CSV))
        stats = load_words(s, read_csv(str(bad)), unit_index, "上册")
        assert len(stats.errors) == 1
        assert "重复" in stats.errors[0]
        assert s.query(Word).count() == 1


def test_unknown_unit_code_is_reported(db, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        WORDS_HEADER + "\nU99,apple,n.,/ˈæpl/, ,1,苹果,,物品,,,,,pending\n",
        encoding="utf-8",
    )
    with db.session() as s:
        unit_index, _ = load_units(s, read_csv(DEFAULT_UNITS_CSV))
        stats = load_words(s, read_csv(str(bad)), unit_index, "上册")
        assert stats.errors
        assert "U99" in stats.errors[0]
        assert s.query(Word).count() == 0


def test_missing_required_cell_is_reported(db, tmp_path):
    bad = tmp_path / "nospell.csv"
    bad.write_text(WORDS_HEADER + "\nSU01,,n.,, ,1,你好,,,,,,,pending\n", encoding="utf-8")
    with db.session() as s:
        unit_index, _ = load_units(s, read_csv(DEFAULT_UNITS_CSV))
        stats = load_words(s, read_csv(str(bad)), unit_index, "上册")
        assert stats.errors
        assert s.query(Word).count() == 0


def test_dry_run_writes_nothing(db):
    """空跑必须一行都不写。"""
    import_seed(db, read_csv(DEFAULT_UNITS_CSV), read_csv(DEFAULT_WORDS_CSV), "上册", commit=False)
    with db.session() as s:
        assert s.query(Book).count() == 0
        assert s.query(Unit).count() == 0
        assert s.query(Word).count() == 0
        assert s.query(WordSense).count() == 0


def test_dry_run_counts_match_real_import(db):
    """空跑报出的「新增」必须等于真实导入的结果。

    这条是给一个真实 bug 上的锁：早期实现用 `if not dry_run` 分支去「模拟」
    导入，导致同一个词的两行被算成两个新词，空跑说「新增 6」而真实只建 5 个。
    用户看到空跑数字来决定要不要导入，数字错了等于保险是假的。
    """
    unit_rows = read_csv(DEFAULT_UNITS_CSV)
    word_rows = read_csv(DEFAULT_WORDS_CSV)

    dry_units, dry_words = import_seed(db, unit_rows, word_rows, "上册", commit=False)
    with db.session() as s:
        assert s.query(Word).count() == 0  # 确实回滚了

    real_units, real_words = import_seed(db, unit_rows, word_rows, "上册", commit=True)

    assert dry_units.books_created == real_units.books_created
    assert dry_units.units_created == real_units.units_created
    assert dry_words.words_created == real_words.words_created
    assert dry_words.senses_created == real_words.senses_created
    # 真实数字本身也要对：50 个词 / 52 个义项 / 18 个单元 / 2 本册
    assert real_words.words_created == 50
    assert real_words.senses_created == 52
    assert real_units.units_created == 18
    assert real_units.books_created == 2


def test_second_sense_row_does_not_move_word_unit(db, tmp_path):
    """多义项的第二行即使写了别的 unit_code，也不能把词搬走。

    模型里 unit_id 的定义是「首次出现单元」。如果更新时跟着 CSV 里的
    unit_code 走，把一个词从 U01 挪到 U02，U01 会凭空少一个词 ——
    而词数又是单元胶囊和抽题池的依据，这种静默迁移极难被发现。
    """
    words = tmp_path / "move.csv"
    words.write_text(
        WORDS_HEADER
        + "\nU01,test,n.,/test/, ,1,测试,,学校,,,,,confirmed"
        + "\nU02,test,n.,/test/, ,2,测验,,学校,,,,,confirmed\n",
        encoding="utf-8",
    )
    with db.session() as s:
        unit_index, _ = load_units(s, read_csv(DEFAULT_UNITS_CSV))
        load_words(s, read_csv(str(words)), unit_index, "上册")

    with db.session() as s:
        word = s.query(Word).filter_by(spelling="test").one()
        unit = s.get(Unit, word.unit_id)
        assert unit.unit_code == "U01", "第二义项不应改写首次出现单元"
        assert len(word.senses) == 2


def test_empty_value_does_not_erase_existing_phonetic(db, tmp_path):
    """补录一行音标留空的记录，不能把已有音标擦掉。

    真实场景：先录了词和音标，后来只想补 accepted，音标列就空着保存了 ——
    如果直接覆盖，音标悄无声息地没了，而界面上「音标写词」题型会直接空题。
    """
    with db.session() as s:
        unit_index, _ = load_units(s, read_csv(DEFAULT_UNITS_CSV))
        load_words(s, read_csv(DEFAULT_WORDS_CSV), unit_index, "上册")

    patch = tmp_path / "patch.csv"
    patch.write_text(
        WORDS_HEADER + "\nSU01,hello,int., ,,1,你好,哈喽,日常交际,,,,,pending\n",
        encoding="utf-8",
    )
    with db.session() as s:
        unit_index, _ = load_units(s, read_csv(DEFAULT_UNITS_CSV))
        load_words(s, read_csv(str(patch)), unit_index, "上册")

    with db.session() as s:
        word = s.query(Word).filter_by(spelling="hello").one()
        assert word.phonetic_uk == "/həˈləʊ/"  # 没被空值擦掉
        assert word.senses[0].accepted == ["哈喽"]  # 但同行的 accepted 确实更新了


def test_cli_dry_run_requires_existing_schema(tmp_path, capsys):
    """空库上跑 --dry-run 应当给出明确指引并返回非零，而不是抛 SQL 异常。"""
    db_path = str(tmp_path / "empty.db")
    code = main(["--db", db_path, "--dry-run"])
    assert code == 2
    out = capsys.readouterr().out
    assert "表结构" in out


def test_cli_init_db_then_dry_run_succeeds(tmp_path, capsys):
    """先 --init-db 建库，之后 --dry-run 应当能正常跑通。"""
    db_path = str(tmp_path / "cli.db")
    assert main(["--db", db_path, "--init-db"]) == 0
    capsys.readouterr()  # 清掉上一轮输出

    assert main(["--db", db_path, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "空跑" in out
    assert "合计词条：50" in out  # 汇总能打印出真实词数（虽然随后会回滚）


def test_cli_dry_run_leaves_db_unchanged(tmp_path, capsys):
    """命令行空跑后，库里不该多出任何一行。

    注意 --init-db 是「迁移 + 导入」两步，跑完之后库里已经有 50 个词了。
    所以要验证「空跑没写入」，正确做法是：给空跑喂一个含新词的 CSV，
    再确认这个新词没有被落库 —— 直接断言 count()==0 是错的。
    """
    db_path = str(tmp_path / "cli2.db")
    assert main(["--db", db_path, "--init-db"]) == 0
    capsys.readouterr()

    extra = tmp_path / "extra.csv"
    extra.write_text(
        WORDS_HEADER + "\nU03,blackboard,n.,/ˈblækbɔːd/, ,1,黑板,,学校,,,,,pending\n",
        encoding="utf-8",
    )
    assert main(["--db", db_path, "--dry-run", "--words", str(extra)]) == 0
    capsys.readouterr()

    from core.db import Database

    db = Database(db_path)
    with db.session() as s:
        assert s.query(Word).count() == 50, "空跑不应写入新词"
        assert s.query(Word).filter_by(spelling="blackboard").count() == 0
    db.dispose()
