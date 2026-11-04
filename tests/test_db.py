"""数据层测试：表结构、约束、级联、时区。

重点不是「能不能 insert」，而是**约束真的会拦住错误数据**。
这些约束如果失效，坏数据会一路流到判题和统计里，那时候已经查不出源头了。
"""
import datetime as dt

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from core.db import Database
from core.models import Book, PracticeItem, PracticeSession, SkillProgress, Unit, Word, WordSense

EXPECTED_TABLES = {
    "books",
    "units",
    "words",
    "word_senses",
    "practice_sessions",
    "practice_items",
    "skill_progress",
}


# ─────────────────────────────────────────────────────────────
# 辅助
# ─────────────────────────────────────────────────────────────


def make_book(session, term="上册") -> Book:
    book = Book(
        publisher="人教版",
        edition="2024",
        grade="七年级",
        term=term,
        title=f"人教版（2024）英语七年级{term}",
    )
    session.add(book)
    session.flush()
    return book


def make_unit(session, book: Book, code="U01", name="You and Me") -> Unit:
    unit = Unit(
        book_id=book.id,
        unit_code=code,
        unit_no=1,
        unit_name=name,
        sort_order=1,
    )
    session.add(unit)
    session.flush()
    return unit


def make_word(session, unit: Unit, spelling="environment", pos="n.") -> Word:
    word = Word(spelling=spelling, pos=pos, unit_id=unit.id)
    session.add(word)
    session.flush()
    return word


def make_sense(session, word: Word, meaning="环境", order=1, accepted=None) -> WordSense:
    sense = WordSense(
        word_id=word.id,
        sense_order=order,
        meaning_zh=meaning,
        accepted=accepted or [],
    )
    session.add(sense)
    session.flush()
    return sense


# ─────────────────────────────────────────────────────────────
# 表结构与连接参数
# ─────────────────────────────────────────────────────────────


def test_all_seven_tables_created(db):
    actual = set(inspect(db.engine).get_table_names())
    assert EXPECTED_TABLES <= actual


def test_wal_mode_enabled(db):
    """WAL 关掉的话，导出 PNG（另一个进程）会锁住答题写入。"""
    with db.session() as s:
        assert s.execute(text("PRAGMA journal_mode")).scalar().lower() == "wal"


def test_foreign_keys_pragma_enabled(db):
    """SQLite 默认不校验外键，必须每个连接都显式打开。"""
    with db.session() as s:
        assert s.execute(text("PRAGMA foreign_keys")).scalar() == 1


# ─────────────────────────────────────────────────────────────
# 类型行为
# ─────────────────────────────────────────────────────────────


def test_datetime_reads_back_timezone_aware(db):
    """SQLite 不存时区，UTCDateTime 必须把 UTC 标记补回来。

    这条测试实际防的是「下次复习时间差 8 小时」：
    如果读回来是 naive，srs 里和 aware 时间一比较就会出问题。
    """
    moment = dt.datetime(2026, 11, 4, 9, 0, tzinfo=dt.timezone.utc)
    with db.session() as s:
        book = make_book(s)
        unit = make_unit(s, book)
        word = make_word(s, unit)
        sense = make_sense(s, word)
        s.add(
            SkillProgress(
                word_id=word.id, sense_id=sense.id, skill="spelling", due_at=moment
            )
        )

    with db.session() as s:
        progress = s.query(SkillProgress).one()
        assert progress.due_at.tzinfo is not None
        assert progress.due_at == moment


def test_json_column_roundtrip(db):
    with db.session() as s:
        book = make_book(s)
        unit = make_unit(s, book)
        word = make_word(s, unit)
        make_sense(s, word, accepted=["自然环境", "生态环境"])

    with db.session() as s:
        sense = s.query(WordSense).one()
        assert sense.accepted == ["自然环境", "生态环境"]


# ─────────────────────────────────────────────────────────────
# 唯一约束
# ─────────────────────────────────────────────────────────────


def test_duplicate_word_spelling_and_pos_rejected(db):
    with db.session() as s:
        book = make_book(s)
        unit = make_unit(s, book)
        make_word(s, unit, "book", "n.")
        with pytest.raises(IntegrityError):
            make_word(s, unit, "book", "n.")
        # flush 失败后 Session 必须先 rollback 才能继续用，
        # 否则退出 with 时 commit 会抛 PendingRollbackError
        s.rollback()


def test_same_spelling_different_pos_allowed(db):
    """book 既是名词（书）也可以是动词（预订），词性不同就该是两行。"""
    with db.session() as s:
        book = make_book(s)
        unit = make_unit(s, book)
        make_word(s, unit, "book", "n.")
        make_word(s, unit, "book", "v.")
        assert s.query(Word).count() == 2


def test_duplicate_sense_order_rejected(db):
    with db.session() as s:
        book = make_book(s)
        unit = make_unit(s, book)
        word = make_word(s, unit)
        make_sense(s, word, "环境", order=1)
        with pytest.raises(IntegrityError):
            make_sense(s, word, "自然环境", order=1)
        s.rollback()


def test_duplicate_unit_code_per_book_rejected(db):
    with db.session() as s:
        book = make_book(s)
        make_unit(s, book, code="U01")
        with pytest.raises(IntegrityError):
            make_unit(s, book, code="U01")
        s.rollback()


def test_duplicate_progress_key_rejected(db):
    with db.session() as s:
        book = make_book(s)
        unit = make_unit(s, book)
        word = make_word(s, unit)
        sense = make_sense(s, word)
        s.add(SkillProgress(word_id=word.id, sense_id=sense.id, skill="spelling"))
        with pytest.raises(IntegrityError):
            s.add(SkillProgress(word_id=word.id, sense_id=sense.id, skill="spelling"))
            s.flush()  # session.add 本身不写库，必须显式 flush 才会撞唯一键
        s.rollback()


def test_same_word_different_skill_allowed(db):
    """拼写会了不代表听音会了，必须能分别记两笔。"""
    with db.session() as s:
        book = make_book(s)
        unit = make_unit(s, book)
        word = make_word(s, unit)
        sense = make_sense(s, word)
        s.add(SkillProgress(word_id=word.id, sense_id=sense.id, skill="spelling"))
        s.add(SkillProgress(word_id=word.id, sense_id=sense.id, skill="listening_spelling"))
        assert s.query(SkillProgress).count() == 2


# ─────────────────────────────────────────────────────────────
# CHECK 约束
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("box", [0, 6, -1])
def test_box_level_out_of_range_rejected(db, box):
    """盒子必须是 1~5。越界值会让间隔表查不到，进而静默算出 0 天间隔。"""
    with db.session() as s:
        book = make_book(s)
        unit = make_unit(s, book)
        word = make_word(s, unit)
        sense = make_sense(s, word)
        with pytest.raises(IntegrityError):
            s.add(
                SkillProgress(
                    word_id=word.id, sense_id=sense.id, skill="spelling", box_level=box
                )
            )
            s.flush()
        s.rollback()


# ─────────────────────────────────────────────────────────────
# 级联
# ─────────────────────────────────────────────────────────────


def test_deleting_word_cascades_to_senses(db):
    with db.session() as s:
        book = make_book(s)
        unit = make_unit(s, book)
        word = make_word(s, unit)
        make_sense(s, word, "环境", 1)

    with db.session() as s:
        s.delete(s.query(Word).one())

    with db.session() as s:
        assert s.query(Word).count() == 0
        assert s.query(WordSense).count() == 0


def test_deleting_book_cascades_to_units(db):
    with db.session() as s:
        book = make_book(s)
        make_unit(s, book, "U01")
        make_unit(s, book, "U02")

    with db.session() as s:
        s.delete(s.query(Book).one())

    with db.session() as s:
        assert s.query(Unit).count() == 0


def test_deleting_session_cascades_to_items(db):
    with db.session() as s:
        book = make_book(s)
        unit = make_unit(s, book)
        word = make_word(s, unit)
        sense = make_sense(s, word)
        session_row = PracticeSession(
            mode="zh_to_en", range_type="unit", range_value="U01", size=1
        )
        s.add(session_row)
        s.flush()
        s.add(
            PracticeItem(
                session_id=session_row.id,
                seq=1,
                word_id=word.id,
                sense_id=sense.id,
                mode="zh_to_en",
                prompt_snapshot="环境",
                expected_snapshot="environment",
            )
        )

    with db.session() as s:
        s.delete(s.query(PracticeSession).one())

    with db.session() as s:
        assert s.query(PracticeItem).count() == 0


def test_deleting_unit_keeps_word_but_clears_unit_id(db):
    """删单元不该连带删词：词条是独立资产，只是暂时不挂在任何单元下。"""
    with db.session() as s:
        book = make_book(s)
        unit = make_unit(s, book)
        make_word(s, unit)

    with db.session() as s:
        s.delete(s.query(Unit).one())

    with db.session() as s:
        word = s.query(Word).one()
        assert word.unit_id is None


# ─────────────────────────────────────────────────────────────
# 会话隔离与事务
# ─────────────────────────────────────────────────────────────


def test_session_rolls_back_on_exception(db):
    with pytest.raises(RuntimeError):
        with db.session() as s:
            make_book(s)
            raise RuntimeError("模拟中途失败")

    with db.session() as s:
        assert s.query(Book).count() == 0


def test_two_databases_are_isolated(tmp_path):
    """测试之间不能互相看到数据，否则一个测试失败会连带污染后面一串。"""
    first = Database(str(tmp_path / "a.db"))
    second = Database(str(tmp_path / "b.db"))
    first.create_all()
    second.create_all()
    try:
        with first.session() as s:
            make_book(s)
        with second.session() as s:
            assert s.query(Book).count() == 0
    finally:
        first.dispose()
        second.dispose()
