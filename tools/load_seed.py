"""把种子 CSV 导入数据库。

设计要点：

1. **幂等**：按自然键 upsert（book 用四元组、unit 用 book+code、word 用 spelling+pos、
   sense 用 word+sense_order）。重复执行不会产生重复词条，可以放心多跑几次。

2. **空跑与正式导入走同一条代码路径**：`--dry-run` 不做任何分支模拟，而是照常
   flush，最后整体回滚（见 Database.session(commit=False)）。这样空跑报出的
   「新增 / 更新 / 未变」就是真实导入会得到的结果，不会漂移。

3. **带行号报错**：CSV 里一行写错不该让整个导入静默丢数据。
   所有问题行都会被收集并打印行号，最后汇总「成功 / 跳过 / 失败」。

用法：

    # 空跑，只看结果（不改库）
    python tools/load_seed.py --dry-run

    # 正式导入（默认库 data/app.db）
    python tools/load_seed.py

    # 指定库（例如测试库）
    python tools/load_seed.py --db D:/tmp/test.db

CSV 编码固定为 utf-8-sig（带 BOM）。这样中文 Windows 下用 Excel 直接双击打开
不会乱码；用 Excel 另存后 BOM 一般还在，若被存成 GBK 请另存为「CSV UTF-8」。
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass, field

from sqlalchemy import func

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.db import Database  # noqa: E402
from core.models import Book, Unit, Word, WordSense  # noqa: E402
from core.normalize import split_variants  # noqa: E402

DEFAULT_UNITS_CSV = os.path.join(PROJECT_ROOT, "data", "seed", "units.pep.2024.grade7.csv")
DEFAULT_WORDS_CSV = os.path.join(PROJECT_ROOT, "data", "seed", "words.sample.csv")

UNITS_REQUIRED = (
    "publisher",
    "edition",
    "grade",
    "term",
    "book_title",
    "unit_code",
    "unit_no",
    "unit_name",
    "sort_order",
)
WORDS_REQUIRED = ("unit_code", "spelling", "pos", "meaning_zh")


@dataclass
class UnitStats:
    """册与单元分开计数。

    合并成一个数字会误导：「新增 20」到底是 20 个单元，还是 18 个单元 + 2 本册？
    这 2 本的差别让「单元总数对不上教材目录」这种问题变得很难察觉。
    """

    books_created: int = 0
    units_created: int = 0
    units_updated: int = 0
    units_unchanged: int = 0
    errors: list[str] = field(default_factory=list)

    def render(self) -> str:
        return (
            f"册：新增 {self.books_created}    "
            f"单元：新增 {self.units_created} / 更新 {self.units_updated} / "
            f"未变 {self.units_unchanged} / 失败 {len(self.errors)}"
        )


@dataclass
class WordStats:
    """词与义项分开计数。

    一个词可以有多个义项（class = 班级 / 课），两者数量本来就不相等。
    混在一起数会让人误以为「词条数不对」。
    """

    words_created: int = 0
    words_updated: int = 0
    words_unchanged: int = 0
    senses_created: int = 0
    senses_updated: int = 0
    senses_unchanged: int = 0
    errors: list[str] = field(default_factory=list)

    def render(self) -> str:
        return (
            f"词：新增 {self.words_created} / 更新 {self.words_updated} / "
            f"未变 {self.words_unchanged}    "
            f"义项：新增 {self.senses_created} / 更新 {self.senses_updated} / "
            f"未变 {self.senses_unchanged} / 失败 {len(self.errors)}"
        )


def read_csv(path: str) -> list[dict]:
    """读 CSV。utf-8-sig 会自动吃掉 BOM。"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到 CSV：{path}")
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def check_headers(rows: list[dict], required: tuple[str, ...], path: str) -> None:
    if not rows:
        raise ValueError(f"{path} 是空文件")
    missing = [col for col in required if col not in rows[0]]
    if missing:
        raise ValueError(f"{path} 缺少必需列：{', '.join(missing)}")


def _bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是"}


def _int(value: str, default: int = 0) -> int:
    text = (value or "").strip()
    return int(text) if text else default


def _int_or_none(value: str) -> int | None:
    text = (value or "").strip()
    return int(text) if text else None


def load_units(session, rows: list[dict]) -> tuple[dict[tuple[str, str], Unit], UnitStats]:
    """导入 books / units，返回 (book_term, unit_code) -> Unit 的索引。"""
    stats = UnitStats()
    index: dict[tuple[str, str], Unit] = {}

    for lineno, row in enumerate(rows, start=2):  # 2 = 表头之后的第一行
        publisher = (row.get("publisher") or "").strip()
        edition = (row.get("edition") or "").strip()
        grade = (row.get("grade") or "").strip()
        term = (row.get("term") or "").strip()
        unit_code = (row.get("unit_code") or "").strip()

        if not all([publisher, edition, grade, term, unit_code]):
            stats.errors.append(f"第 {lineno} 行：book 四元组或 unit_code 为空，已跳过")
            continue

        try:
            unit_no = _int(row.get("unit_no", "0"))
            sort_order = _int(row.get("sort_order", "0"))
            planned = _int_or_none(row.get("word_count_planned", ""))
        except ValueError:
            stats.errors.append(
                f"第 {lineno} 行：unit_no/sort_order/word_count_planned 不是整数，已跳过"
            )
            continue

        book = (
            session.query(Book)
            .filter_by(publisher=publisher, edition=edition, grade=grade, term=term)
            .one_or_none()
        )
        if book is None:
            book = Book(
                publisher=publisher,
                edition=edition,
                grade=grade,
                term=term,
                title=(row.get("book_title") or f"{publisher}{edition}{grade}{term}").strip(),
            )
            session.add(book)
            session.flush()
            stats.books_created += 1

        unit = session.query(Unit).filter_by(book_id=book.id, unit_code=unit_code).one_or_none()

        payload = {
            "unit_no": unit_no,
            "is_starter": _bool(row.get("is_starter", "")),
            "unit_name": (row.get("unit_name") or "").strip(),
            "sort_order": sort_order,
            "word_count_planned": planned,
        }
        if unit is None:
            unit = Unit(book_id=book.id, unit_code=unit_code, **payload)
            session.add(unit)
            session.flush()
            stats.units_created += 1
        else:
            changed = False
            for key, value in payload.items():
                if getattr(unit, key) != value:
                    setattr(unit, key, value)
                    changed = True
            if changed:
                stats.units_updated += 1
            else:
                stats.units_unchanged += 1

        index[(term, unit_code)] = unit

    return index, stats


def load_words(session, rows: list[dict], unit_index, default_term: str) -> WordStats:
    """导入 words / word_senses。"""
    stats = WordStats()
    seen: set[tuple[str, str, int]] = set()

    for lineno, row in enumerate(rows, start=2):
        spelling = (row.get("spelling") or "").strip()
        pos = (row.get("pos") or "").strip()
        unit_code = (row.get("unit_code") or "").strip()
        meaning = (row.get("meaning_zh") or "").strip()

        if not spelling or not meaning:
            stats.errors.append(f"第 {lineno} 行：spelling 或 meaning_zh 为空，已跳过")
            continue

        term = (row.get("term") or default_term).strip()
        unit = unit_index.get((term, unit_code))
        if unit is None:
            stats.errors.append(
                f"第 {lineno} 行：unit_code={unit_code!r} 在单元表中不存在，已跳过（先导入单元表）"
            )
            continue

        try:
            sense_order = _int(row.get("sense_order", "1"), default=1)
        except ValueError:
            stats.errors.append(f"第 {lineno} 行：sense_order 不是整数，已跳过")
            continue

        dup_key = (spelling.lower(), pos.lower(), sense_order)
        if dup_key in seen:
            stats.errors.append(
                f"第 {lineno} 行：CSV 内重复（{spelling}/{pos} 义项 {sense_order}），已跳过"
            )
            continue
        seen.add(dup_key)

        # 可覆盖字段。unit_id 刻意不在其中 —— 模型里 unit_id 的定义是
        # 「首次出现单元」，如果多义项的某一行写了别的 unit_code，
        # 把它跟着改会把词从原单元静默搬走，原单元凭空少一个词。
        word_payload = {
            "theme": (row.get("theme") or "").strip() or None,
            "phonetic_uk": (row.get("phonetic_uk") or "").strip() or None,
            "phonetic_us": (row.get("phonetic_us") or "").strip() or None,
            "source": (row.get("source") or "PEP2024").strip(),
            "source_license": (row.get("source_license") or "").strip(),
            "verify_status": (row.get("verify_status") or "pending").strip(),
        }

        word = session.query(Word).filter_by(spelling=spelling, pos=pos).one_or_none()
        if word is None:
            word = Word(spelling=spelling, pos=pos, unit_id=unit.id, **word_payload)
            session.add(word)
            session.flush()
            stats.words_created += 1
        else:
            changed = False
            for key, value in word_payload.items():
                # 音标/主题留空时不覆盖已有的值，避免「补录一行空值把原数据擦掉」
                if value in (None, "") and getattr(word, key):
                    continue
                if getattr(word, key) != value:
                    setattr(word, key, value)
                    changed = True
            if changed:
                stats.words_updated += 1
            else:
                stats.words_unchanged += 1

        accepted = split_variants(row.get("accepted", ""))
        sense_payload = {
            "meaning_zh": meaning,
            "pos": pos or None,
            "accepted": accepted,
            "example_en": (row.get("example_en") or "").strip() or None,
            "example_zh": (row.get("example_zh") or "").strip() or None,
        }
        sense = (
            session.query(WordSense)
            .filter_by(word_id=word.id, sense_order=sense_order)
            .one_or_none()
        )
        if sense is None:
            session.add(WordSense(word_id=word.id, sense_order=sense_order, **sense_payload))
            session.flush()
            stats.senses_created += 1
        else:
            changed = False
            for key, value in sense_payload.items():
                if getattr(sense, key) != value:
                    setattr(sense, key, value)
                    changed = True
            if changed:
                stats.senses_updated += 1
            else:
                stats.senses_unchanged += 1

    return stats


def print_unit_summary(session, term: str | None = None) -> None:
    """打印每个单元的**实际**词数。

    这个数字就是设置页「Unit 3 · 20 词」胶囊的真实来源。
    如果它和教材词表差很多，说明这一单元的词还没录全 —— 这正是
    「胶囊写 20、实际只有 13」那个 bug 的根因，所以必须由数据库算，不能硬编码。
    """
    counts = dict(
        session.query(Word.unit_id, func.count(Word.id)).group_by(Word.unit_id).all()
    )

    query = (
        session.query(
            Book.term,
            Unit.id,
            Unit.unit_code,
            Unit.unit_name,
            Unit.word_count_planned,
        )
        .join(Unit, Unit.book_id == Book.id)
        .order_by(Book.term, Unit.sort_order)
    )
    if term:
        query = query.filter(Book.term == term)

    rows = query.all()
    print("\n每个单元的实际词数：")
    print(f"  {'册':<4}{'单元':<8}{'名称':<26}{'实际':>6}{'计划':>8}")
    total = 0
    empty: list[str] = []
    for book_term, unit_id, code, name, planned in rows:
        actual = counts.get(unit_id, 0)
        total += actual
        if actual == 0:
            empty.append(f"{book_term}/{code}")
        planned_text = str(planned) if planned is not None else "-"
        print(f"  {book_term:<4}{code:<8}{name:<26}{actual:>6}{planned_text:>8}")
    print(f"  合计词条：{total}")
    if empty:
        print(f"  还没有词的单元（共 {len(empty)} 个）：{'、'.join(empty)}")


def ensure_schema(database: Database, init_db: bool, dry_run: bool) -> bool:
    """确认库里有表结构；缺表时给出明确指引，或按 --init-db 自动迁移。

    为什么不让加载器直接 create_all：
    create_all 建出来的表没有任何迁移记录，之后 alembic upgrade 会认为
    库是空的并重复建表，直接报「table already exists」。
    所以建表只有一条路：alembic upgrade head。

    注意空跑也需要表：空跑只是不提交，照样要能 SELECT 判断「已存在」。
    """
    from sqlalchemy import inspect

    if inspect(database.engine).has_table("books"):
        return True

    if dry_run:
        print(f"数据库还没有表结构，空跑同样需要能读表（当前库：{database.path}）")
        print("先执行迁移，再空跑：")
        print("  .\\.venv\\Scripts\\python.exe -m alembic upgrade head")
        return False

    if not init_db:
        print("数据库还没有表结构，先执行迁移：")
        print(
            f"  .\\.venv\\Scripts\\python.exe -m alembic upgrade head   （当前库：{database.path}）"
        )
        print("或本次直接加 --init-db 让加载器代跑迁移。")
        return False

    from alembic import command
    from alembic.config import Config

    cfg = Config(os.path.join(PROJECT_ROOT, "alembic.ini"))
    previous = os.environ.get("ECARD_DB_PATH")
    os.environ["ECARD_DB_PATH"] = database.path  # env.py 从这里取库路径
    try:
        command.upgrade(cfg, "head")
    finally:
        if previous is None:
            os.environ.pop("ECARD_DB_PATH", None)
        else:
            os.environ["ECARD_DB_PATH"] = previous
    print(f"已执行 alembic upgrade head -> {database.path}\n")
    return True


def import_seed(database: Database, unit_rows, word_rows, term: str, commit: bool):
    """跑一次完整导入，返回 (unit_stats, word_stats)。

    commit=False 时数据在会话内可见（用于打印汇总），退出后整体回滚。
    """
    with database.session(commit=commit) as session:
        unit_index, unit_stats = load_units(session, unit_rows)
        word_stats = load_words(session, word_rows, unit_index, term)

        print(unit_stats.render())
        print(word_stats.render())

        errors = unit_stats.errors + word_stats.errors
        if errors:
            print(f"\n有 {len(errors)} 行被跳过：")
            for item in errors:
                print(f"  - {item}")

        # 必须在会话内打印：空跑模式下这些数据稍后会被回滚
        print_unit_summary(session, term=None)

        if not commit:
            print("\n（空跑模式：以上结果已整体回滚，数据库中没有任何改动）")

    return unit_stats, word_stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="导入种子词库 CSV")
    parser.add_argument("--units", default=DEFAULT_UNITS_CSV, help="单元 CSV 路径")
    parser.add_argument("--words", default=DEFAULT_WORDS_CSV, help="词条 CSV 路径")
    parser.add_argument("--db", default=None, help="数据库文件路径，默认 data/app.db")
    parser.add_argument("--dry-run", action="store_true", help="正常执行但最后回滚，不改库")
    parser.add_argument("--init-db", action="store_true", help="库为空时先跑 alembic 迁移")
    parser.add_argument("--term", default="上册", help="词条 CSV 未写 term 列时使用的册别")
    args = parser.parse_args(argv)

    if args.dry_run and args.init_db:
        print("--dry-run 与 --init-db 不能同时使用（空跑不应该改库结构）")
        return 2

    database = Database(args.db)
    mode = "空跑（执行后回滚，不改库）" if args.dry_run else "正式导入"
    print(f"数据库：{database.path}")
    print(f"模式：{mode}\n")

    if not ensure_schema(database, args.init_db, args.dry_run):
        database.dispose()
        return 2

    unit_rows = read_csv(args.units)
    check_headers(unit_rows, UNITS_REQUIRED, args.units)
    word_rows = read_csv(args.words)
    check_headers(word_rows, WORDS_REQUIRED, args.words)

    unit_stats, word_stats = import_seed(
        database, unit_rows, word_rows, args.term, commit=not args.dry_run
    )

    database.dispose()
    return 1 if (unit_stats.errors or word_stats.errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
