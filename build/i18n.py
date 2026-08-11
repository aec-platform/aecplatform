"""Interface strings for the two languages the site ships in.

Product copy lives in the registry; this module only holds chrome — nav labels,
section headings, the words around a number. Adding a third language means
adding a third key to every entry here and to every i18n object in
``registry/products.json``; :func:`check` is what tells you when you missed one.
"""

from __future__ import annotations

LANGS = ("en", "vi")

# The path prefix each language is served under. English is the apex.
PREFIX = {"en": "", "vi": "vi/"}

LABEL = {
    "en": "English",
    "vi": "Tiếng Việt",
}

STRINGS: dict[str, dict[str, str]] = {
    "nav_products": {"en": "Products", "vi": "Sản phẩm"},
    "nav_open": {"en": "Open source", "vi": "Mã nguồn mở"},
    "nav_thesis": {"en": "Why", "vi": "Vì sao"},
    "nav_contact": {"en": "Contact", "vi": "Liên hệ"},
    "nav_app": {"en": "Sign in", "vi": "Đăng nhập"},
    "hero_cta_primary": {"en": "Browse the open tools", "vi": "Xem bộ công cụ mở"},
    "hero_cta_secondary": {"en": "Talk to us", "vi": "Liên hệ với chúng tôi"},
    "thesis_heading": {"en": "Why this exists", "vi": "Vì sao có dự án này"},
    "stack_heading": {"en": "How it stacks", "vi": "Cách các tầng xếp lên nhau"},
    "stack_note": {
        "en": "Not a diagram of an intention. qto and plancheck import ifc-spf; "
        "ecfactors imports qto. The arrows are in the dependency metadata.",
        "vi": "Đây không phải sơ đồ ý tưởng. qto và plancheck import ifc-spf; "
        "ecfactors import qto. Các mũi tên lấy thẳng từ khai báo phụ thuộc.",
    },
    "numbers_products": {"en": "products", "vi": "sản phẩm"},
    "numbers_open": {"en": "open-source tools", "vi": "công cụ mã nguồn mở"},
    "numbers_tests": {"en": "tests across the open toolchain", "vi": "test trên toàn bộ công cụ mở"},
    # Deliberately "third-party": qto requires ifc-spf, which is ours, and
    # ifctrap's ifcopenshell is an optional extra. The unqualified claim would
    # have been false.
    "numbers_deps": {
        "en": "third-party runtime dependencies",
        "vi": "thư viện bên thứ ba phải cài",
    },
    "product_status": {"en": "Status", "vi": "Trạng thái"},
    "product_license": {"en": "License", "vi": "Giấy phép"},
    "product_language": {"en": "Language", "vi": "Ngôn ngữ"},
    "product_tests": {"en": "Tests", "vi": "Số test"},
    "product_install": {"en": "Install", "vi": "Cài đặt"},
    "product_not_on_index": {
        "en": "Not on PyPI yet — this installs from source.",
        "vi": "Chưa lên PyPI — lệnh này cài trực tiếp từ mã nguồn.",
    },
    "product_run": {"en": "Run", "vi": "Chạy thử"},
    "product_highlights": {"en": "What makes it different", "vi": "Điểm khác biệt"},
    "product_builds_on": {"en": "Builds on", "vi": "Xây trên"},
    "product_used_by": {"en": "Used by", "vi": "Được dùng bởi"},
    "product_source": {"en": "Source", "vi": "Mã nguồn"},
    # Two different reasons a repository has no link yet, and they must not be
    # conflated: a commercial product is closed on purpose, an MIT tool is
    # simply not pushed yet.
    "product_source_private": {
        "en": "Source is private during the pilot. Ask for access.",
        "vi": "Mã nguồn đang đóng trong giai đoạn thí điểm. Liên hệ để được cấp quyền.",
    },
    "product_source_unpublished": {
        "en": "Open source, not yet published — the repository goes public with "
        "the org migration.",
        "vi": "Mã nguồn mở, chưa công bố — kho mã sẽ mở công khai cùng đợt chuyển "
        "về tổ chức.",
    },
    "back_home": {"en": "All products", "vi": "Tất cả sản phẩm"},
    "contact_heading": {"en": "Get in touch", "vi": "Liên hệ"},
    "contact_body": {
        "en": "Pilots, partnerships, or a bug in one of the open tools — the same "
        "inbox reads all three.",
        "vi": "Thí điểm, hợp tác, hay báo lỗi một công cụ mở — cùng một hòm thư "
        "đọc cả ba.",
    },
    "footer_rights": {
        "en": "Open tools under MIT. Products under their own licences.",
        "vi": "Công cụ mở theo giấy phép MIT. Sản phẩm theo giấy phép riêng.",
    },
    "not_found_title": {"en": "No such page", "vi": "Không có trang này"},
    "not_found_body": {
        "en": "The link is wrong or the page moved. The product list is a good place to restart.",
        "vi": "Liên kết sai hoặc trang đã chuyển. Bắt đầu lại từ danh sách sản phẩm là hợp lý nhất.",
    },
}

STATUS: dict[str, dict[str, str]] = {
    "alpha": {"en": "Alpha", "vi": "Thử nghiệm sớm"},
    "beta": {"en": "Beta", "vi": "Thử nghiệm"},
    "stable": {"en": "Stable", "vi": "Ổn định"},
    "private-beta": {"en": "Private beta", "vi": "Thí điểm giới hạn"},
    "research": {"en": "Research", "vi": "Nghiên cứu"},
}


def t(key: str, lang: str) -> str:
    """Look up an interface string, failing loudly on a missing translation."""
    try:
        return STRINGS[key][lang]
    except KeyError as exc:  # pragma: no cover - guarded by check()
        raise KeyError(f"no {lang!r} string for {key!r}") from exc


def check() -> list[str]:
    """Return the coverage gaps, so CI can refuse an untranslated build."""
    gaps = []
    for key, values in STRINGS.items():
        for lang in LANGS:
            if not values.get(lang):
                gaps.append(f"STRINGS[{key!r}][{lang!r}]")
    for key, values in STATUS.items():
        for lang in LANGS:
            if not values.get(lang):
                gaps.append(f"STATUS[{key!r}][{lang!r}]")
    return gaps
