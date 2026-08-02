"""Live-LLM translation evals: real API calls, no fakes.

These tests exercise the full production path (``translate_cards`` with the
real OpenCode Go translator: batch retry/split machinery, source-echo
alignment check, JSON response mode, deterministic temperature) against the
specific content shapes that have caused problems in production:

- dense 19th-century prose that truncated mid-response
- archaic/alternative word forms the model transcribes differently in its
  echo ("сестрою" vs "сестрой")
- cards starting with numbers/brackets whose echo picks up the list prefix
- multi-line verse that used to compress to a first-line-only translation
- multi-sentence cards that used to compress to their first sentence
- whitespace-only cards that could not be aligned at all
- single very long cards (the deepest split level)

Run with ``RUN_EVALS=1 uv run pytest evals/ -q``. These spend real API quota.
"""

from book_to_flashcards.Card import Card
from book_to_flashcards.opencode_translator import OpenCodeGoTranslator
from book_to_flashcards.translate_cards import translate_cards

MIN_RATIO = 0.5  # full translations are ~0.9-1.4x the source; compressed ~0.3x


def make_cards(title, author, texts):
    pos = 0
    cards = []
    for t in texts:
        cards.append(
            Card(title=title, author=author, start=pos, end=pos + len(t), text=t)
        )
        pos += len(t) + 1
    return cards


def run_batch(texts, batch_size=30):
    translator = OpenCodeGoTranslator(batch_size=batch_size)
    cards = make_cards("Eval", "Eval Author", texts)
    return list(translate_cards(cards, translator, "English"))


def assert_complete(out, texts):
    assert len(out) == len(texts), "card count changed"
    assert all(c.translation for c in out), "some cards came back untranslated"


def assert_full_coverage(out):
    """Each translation must cover its whole card (no first-line compression)."""
    for c in out:
        assert len(c.translation) >= MIN_RATIO * len(c.text), (
            f"translation looks compressed: {len(c.translation)} chars for "
            f"{len(c.text)} chars: {c.translation[:60]!r}"
        )


def test_dense_prose_batch_truncation_recovery():
    # Учитель (Чехов): dense prose that truncated 60-card batches and stranded
    # the book at the deepest split level
    texts = [
        ("Федор Лукич Сысоев, учитель фабричной школы, содержимой на счет Мануфактуры Куликина сыновья, готовился "
        "к празднику и купил себе на сбереженные деньги новую пару брюк, но тотчас же, на другой же день, "
        "успел сесть на гвоздик и вырезал в брюках преглупейшую дыру."),
        ("Зашивать брюки было некому: мать Федора Лукича умерла, а жена его, хотя и была хорошая женщина, "
        "но не умела ничего шить, и, по совести сказать, до такой степени была избалована своим мужем, "
        "что считала это занятие ниже своего достоинства."),
        ("Поэтому Федор Лукич прибег к экстренным мерам: он решил обратиться к своему знакомому, "
        "учителю прогимназии, который, как ему было известно, отлично умел зашивать дыры."),
    ]
    out = run_batch(texts)
    assert_complete(out, texts)
    assert_full_coverage(out)


def test_archaic_form_echo_variant():
    # Бесы (Достоевский): the model echoed "сестрою" where the card has
    # "сестрой"; the exact-prefix alignment check looped forever on this
    texts = [
        ("С сестрой своею Дашей, тоже воспитанницей Варвары Петровны, жившею у ней фавориткой на самой "
        "благородной ноге, Лизавета Николаевна, еще в детстве, была связана самою нежною дружбой."),
        ("Но Даша, девушка лет двадцати, скромная и рассудительная, никогда не выказывала своей дружбы "
        "так пылко, как Лизавета Николаевна."),
    ]
    out = run_batch(texts)
    assert_complete(out, texts)
    assert_full_coverage(out)


def test_bracket_starting_card():
    # Борис Годунов (Пушкин): the card starts with "(1598 года, 20 февраля)"
    # and the model's echo picked up the prompt's "[N] " numbering prefix
    texts = [
        ("(1598 года, 20 февраля)\nи Воротынский\nНаряжены мы вместе город ведать,\n"
        "Но, кажется, нам не за кем смотреть:\n"),
        "Москва пуста; вослед за патриархом\nК монастырю пошел и весь народ.\n",
    ]
    out = run_batch(texts)
    assert_complete(out, texts)
    assert_full_coverage(out)


def test_multiline_verse_translates_fully():
    # На поле Куликовом (Блок): multi-line verse that used to compress to a
    # first-line-only translation in large batches
    texts = [
        "Река раскинулась. Течет, грустит лениво\nИ моет берега.\nНад скудной глиной желтого обрыва\n",
        "В степи грустят стога.\nО, Русь моя! Жена моя! До боли\nНам ясен долгий путь!\n",
    ]
    out = run_batch(texts)
    assert_complete(out, texts)
    assert_full_coverage(out)


def test_multisentence_card_translates_fully():
    # Гранатовый браслет (Куприн): the model used to translate only the first
    # sentence of a two-sentence card in big batches
    texts = [
        "по зеленому сукну.\nЯ давно настаивал!  ",
        ("Она достала из своего ручного мешочка маленькую записную книжку в удивительном переплете: "
        "на старом, стершемся и посеревшем от времени синем бархате вился глухой золотой узор."),
    ]
    out = run_batch(texts)
    assert_complete(out, texts)
    assert_full_coverage(out)


def test_whitespace_only_card_in_batch():
    # whitespace-only cards cannot produce an echo; the alignment check is
    # skipped for them and the batch must still complete
    texts = [
        "Он взглянул на часы и поспешил к выходу.",
        "\n",
        "На улице шел мелкий осенний дождь.",
    ]
    out = run_batch(texts)
    assert_complete(out, texts)


def test_verse_epigraph_batch():
    # Бесы (Достоевский) opens with a verse epigraph; verse + prose mixed in
    # one batch used to trigger retry storms
    texts = [
        "Хоть убей, следа не видно,\nСбились мы, что делать нам?\nВ поле бес нас водит, видно,\n",
        "Домой приехали поздно, когда на дворе уже совсем стемнело, и в комнатах было не особенно светло.",
        "Степан Трофимович стоял у окна и смотрел на пустую улицу, залитую холодным лунным светом.",
    ]
    out = run_batch(texts)
    assert_complete(out, texts)
    assert_full_coverage(out)


def test_long_single_card():
    # Записки из Мертвого дома (Достоевский): a single very long dense card -
    # the deepest split level, where the alignment check is skipped
    text = (
        "В отдаленных краях Сибири, среди степей, гор или непроходимых лесов, попадаются изредка "
        "маленькие города, с одной, много с двумя тысячами жителей, деревянные, невзрачные, "
        "с двумя церквами - одной в городе, другой на кладбище, - города, похожие более на хорошее "
        "подмосковное село, чем на город."
    )
    out = run_batch([text])
    assert_complete(out, [text])
    assert_full_coverage(out)


def test_temperature_zero_output_is_complete():
    # temperature 0 is near-deterministic but not byte-guaranteed across
    # requests (batched inference, sampling kernels); assert the contract that
    # matters: both runs are complete and not compressed
    texts = [
        ("Он долго стоял на одном месте, чмокал губами и, точно жалея расстаться с дремотою, "
        "лениво чесал грудь и голову."),
        "Кругом было тихо; только изредка слышался легкий шорох ветра в сухой траве.",
    ]
    for _ in range(2):
        out = run_batch(texts)
        assert_complete(out, texts)
        assert_full_coverage(out)
