import pytest
import sys
sys.path.insert(0, r'C:\Users\minam\code\stardew-bilin\BilingualModBuilder')

from parsers import (
    bilingualize_pair,
    _bilingualize_y_text,
    _bilingualize_segments,
    bilingualize_event_quoted_text,
    make_dialogue_bilingual,
)


class TestBilingualizeYText:
    """_bilingualize_y_text — $y quick question bilingualization."""

    def test_basic_y(self):
        en = "$y 'How's everything going?_Good!_Great!'"
        zh = "$y '一切都好吗？_不错！_太棒了！'"
        expected = "$y 'How's everything going? / 一切都好吗？_Good! / 不错！_Great! / 太棒了！'"
        assert _bilingualize_y_text(en, zh) == expected

    def test_y_with_options_and_responses(self):
        en = "$y 'Do you think it's ready?_Yes_I agree._No_Let's wait.'"
        zh = "$y '你觉得好了吗？_是_我也觉得。_不_再等等吧。'"
        expected = "$y 'Do you think it's ready? / 你觉得好了吗？_Yes / 是_I agree. / 我也觉得。_No / 不_Let's wait. / 再等等吧。'"
        assert _bilingualize_y_text(en, zh) == expected

    def test_y_with_apostrophes(self):
        en = "$y 'Don't you think it's great?_Yes_I'm sure._No_I don't know.'"
        zh = "$y '你不觉得很好吗？_是_我确定。_不_我不知道。'"
        result = _bilingualize_y_text(en, zh)
        assert result is not None
        assert result.startswith("$y '")
        assert result.endswith("'")
        # Verify structure preserved: Q_Opt1_Resp1_Opt2_Resp2
        parts = result[4:-1].split('_')  # strip "$y '" and "'"
        assert len(parts) == 5
        assert ' / ' in parts[0]  # question is bilingual
        assert ' / ' in parts[1]  # option 1 is bilingual

    def test_y_with_emotion_codes(self):
        en = "$y 'Are you ready?_Yes_Let's go!$h_No_I need more time.$s'"
        zh = "$y '准备好了吗？_好了_我们走吧！$h_还没_我还要再准备一下。$s'"
        expected = "$y 'Are you ready? / 准备好了吗？_Yes / 好了_Let's go!$h / 我们走吧！$h_No / 还没_I need more time.$s / 我还要再准备一下。$s'"
        assert _bilingualize_y_text(en, zh) == expected

    def test_y_with_gender_split_in_segment(self):
        en = "$y 'Welcome^Welcome, sir_Hello^Hello, sir'"
        zh = "$y '欢迎^欢迎，先生_你好^你好，先生'"
        # Each segment is bilingualized individually, then joined by _
        result = _bilingualize_y_text(en, zh)
        assert result is not None
        # Check the ^ is preserved in each segment
        parts = result[4:-1].split('_')
        assert '^' in parts[0]
        assert '^' in parts[1]

    def test_y_segment_count_mismatch_returns_none(self):
        en = "$y 'Q_Opt1_Resp1'"
        zh = "$y 'Q_Opt1_Resp1_Opt2_Resp2'"
        assert _bilingualize_y_text(en, zh) is None

    def test_non_y_returns_none(self):
        en = "Just normal text"
        zh = "就是普通文字"
        assert _bilingualize_y_text(en, zh) is None

    def test_y_only_in_one_language_returns_none(self):
        en = "$y 'Hello_World'"
        zh = "普通文字"
        assert _bilingualize_y_text(en, zh) is None

    def test_y_missing_quotes_returns_none(self):
        en = "$y Hello_World"
        zh = "$y 你好_世界"
        assert _bilingualize_y_text(en, zh) is None


class TestBilingualizePairWithY:
    """bilingualize_pair — integration with $y detection."""

    def test_bilingualize_pair_handles_y(self):
        en = "$y 'Ready?_Yes_Go!$h'"
        zh = "$y '准备好了吗？_好了_出发！$h'"
        result = bilingualize_pair(en, zh)
        # Should produce a single $y block with bilingual segments
        assert result.count("$y") == 1  # not 2!
        assert result.startswith("$y '")
        assert result.endswith("'")
        assert " / " in result

    def test_bilingualize_pair_normal_text_unchanged(self):
        en = "Hello there!"
        zh = "你好！"
        assert bilingualize_pair(en, zh) == "Hello there! / 你好！"

    def test_bilingualize_pair_with_caret_only(self):
        en = "Welcome^Welcome, sir"
        zh = "欢迎^欢迎，先生"
        expected = "Welcome / 欢迎^Welcome, sir / 欢迎，先生"
        assert bilingualize_pair(en, zh) == expected


class TestBilingualizeSegmentsWithY:
    """_bilingualize_segments — $y inside #$b# segmented text."""

    def test_y_with_b_sep_before(self):
        """$y block followed by #$b# (Penny's case, both languages same structure)."""
        en = "$y 'Q_Opt1_Resp1'#$b#Continue..."
        zh = "$y 'Q_Opt1_Resp1'#$b#继续……"
        result = _bilingualize_segments(en, zh)
        assert result.count("$y") == 1
        assert " / " in result

    def test_y_with_b_sep_inside_en_only(self):
        """#$b# inside $y response in EN but not ZH (Linus case)."""
        en = "$y 'Q_Opt1_Resp1_Opt2_Sigh...#$b#Not everyone.'"
        zh = "$y 'Q_Opt1_Resp1_Opt2_唉……不是所有人。'"
        # The $y block has 5 segments in both languages (Q, Opt1, Resp1, Opt2, Resp2)
        # But Resp2 has #$b# in EN only, causing segment count mismatch in _bilingualize_segments
        # However, bilingualize_pair now intercepts $y before _bilingualize_segments
        result = _bilingualize_segments(en, zh)
        # Should still produce valid single $y block
        assert result.count("$y") == 1
        assert result.startswith("$y '") or result.startswith("$y '")
        # The #$b# within a segment is preserved
        assert "#$b#" in result

    def test_y_without_b_sep_unchanged_structure(self):
        """Plain $y block, no #$b# at all."""
        en = "$y 'Q_Opt1_Resp1'"
        zh = "$y 'Q_Opt1_Resp1'"
        result = _bilingualize_segments(en, zh)
        assert result.count("$y") == 1
        parts = result[4:-1].split('_')
        assert len(parts) == 3


class TestBilingualizeEventQuotedTextWithY:
    """bilingualize_event_quoted_text — $y in event speak commands."""

    def test_event_y_simple(self):
        en = "$y 'Do you think there's something wrong?_Yes_Disgusting.'"
        zh = "$y '你觉得有问题吗？_是_很恶心。'"
        result = bilingualize_event_quoted_text(en, zh)
        assert result.count("$y") == 1
        assert " / " in result

    def test_event_y_standalone(self):
        """$y standalone — the common real-world case."""
        en = "$y 'Q_Opt1_Resp1'"
        zh = "$y 'Q_Opt1_Resp1'"
        # When both are identical, function returns en_text directly
        result = bilingualize_event_quoted_text(en, zh)
        assert result == en
        assert result.count("$y") == 1

    def test_event_y_different_text(self):
        """$y with different EN/ZH text."""
        en = "$y 'Q_Opt1_Resp1'"
        zh = "$y '问_选项1_回答1'"
        result = bilingualize_event_quoted_text(en, zh)
        assert result.count("$y") == 1
        assert " / " in result

    def test_event_y_with_b_sep_before(self):
        """$y with #$b# separator before it (Phone_Ring_Lewis pattern)."""
        en = "Hey @.#$b#Check this.#$b#$y 'How's it going?_Good!_Great!'"
        zh = "你好@。#$b#看这个。#$b#$y '怎么样？_不错！_太棒了！'"
        result = bilingualize_event_quoted_text(en, zh)
        assert result.count("$y") == 1
        assert " / " in result
        # Segments before $y are also bilingualized
        assert " / " in result[:30]  # "Hey @." segment has separator


class TestMakeDialogueBilingualWithY:
    """make_dialogue_bilingual — $y in character dialogue."""

    def test_caroline_house_upgrade(self):
        """Real-world: Caroline's houseUpgrade_1 dialogue."""
        en = "$y 'I heard you got a new kitchen! Think you'll be doing a lot of cooking?_I plan to!_It's a good skill to have. And with all those fresh ingredients on your farm, you'll be sitting pretty!_Nah, it's just for looks_I see. Well, don't forget to eat right... nutrition is important.'"
        zh = "$y '我听说你有了个新厨房！你会经常做饭吗？_我正有此意！_会做饭可是很实用的，你还有农场上的新鲜食材，条件可谓是得天独厚！_没有，只是撑个门面。_好吧，不过还是要健康膳食……营养是很重要的。'"
        result = make_dialogue_bilingual(en, zh)
        assert result.count("$y") == 1
        assert " / " in result
        # Verify structure: opening $y and closing '
        assert result.startswith("$y '")
        assert result.endswith("'")

    def test_jas_crop_matured(self):
        """Real-world: Jas cropMatured_595 dialogue."""
        en = "$y 'Um... Have you ever seen a fairy?_Yes_Wow! I wanna see one, too.$h_No_...Me neither.$s'"
        zh = "$y '呃……你见过仙子吗？_见过_哇！我也想看看。$h_没见过_……我也没有。$s'"
        result = make_dialogue_bilingual(en, zh)
        assert result.count("$y") == 1
        assert " / " in result

    def test_linus_festival_dialogue(self):
        """Real-world: Linus dialogue in festivals (if applicable)."""
        en = "$y 'Are you having fun?_Yes_Me too!$h_No_That's too bad.$s'"
        zh = "$y '你玩得开心吗？_开心_我也是！$h_不开心_太可惜了。$s'"
        result = make_dialogue_bilingual(en, zh)
        assert result.count("$y") == 1
        assert " / " in result


class TestCookingChannelBilingual:
    """Simulate Data/TV/CookingChannel bilingualization."""

    def _simulate_cooking_bilingual(self, en_val, zh_val):
        """Replicate the logic from build_bilingual_pack.py for testing."""
        if '/' in en_val and '/' in zh_val:
            recipe_name, en_dialogue = en_val.split('/', 1)
            _, zh_dialogue = zh_val.split('/', 1)
            return f"{recipe_name}/{bilingualize_pair(en_dialogue, zh_dialogue)}"
        return bilingualize_pair(en_val, zh_val)

    def test_coleslaw(self):
        en = "Coleslaw/Coleslaw! Envisioning bland mounds of limp cabbage? You're not alone. But a great coleslaw can be so much more. Make sure you have juicy fresh cabbage for this one. Toss with a little vinegar and mayonnaise and you're all set. Ah, that's crisp."
        zh = "Coleslaw/卷心菜沙拉！想吃上一大盘清淡而柔软的卷心菜？不光是你有这样的想法。其实卷心菜沙拉可以做得更加美味。做这道菜，一定要选取多汁、新鲜的卷心菜。撒上一点醋和沙拉酱就可以了。啊，非常脆爽。"
        result = self._simulate_cooking_bilingual(en, zh)
        # Recipe name prefix (before first /) is exactly the recipe name
        recipe_prefix = result.split("/")[0]
        assert recipe_prefix == "Coleslaw"
        # Bilingual separator present in dialogue portion
        assert " / " in result
        # Chinese dialogue does NOT start with "Coleslaw/"
        after_sep = result.split(" / ", 1)[1]
        assert "Coleslaw/" not in after_sep

    def test_stir_fry(self):
        en = "Stir Fry/Stir Fry! It's a perfect way to get some healthy greens on your plate."
        zh = "Stir Fry/蔬菜什锦饭是让你能吃到健康蔬菜的最佳方式。"
        result = self._simulate_cooking_bilingual(en, zh)
        assert result.split("/")[0] == "Stir Fry"
        # Chinese portion should not have "Stir Fry/" prefix
        after_sep = result.split(" / ", 1)[1]
        assert "Stir Fry/" not in after_sep

    def test_no_slash_fallback(self):
        """If no / in value, fall back to normal bilingualize_pair."""
        en = "SimpleText"
        zh = "简单文本"
        result = self._simulate_cooking_bilingual(en, zh)
        assert result == "SimpleText / 简单文本"

    def test_recipe_different_in_en_zh_uses_en(self):
        """If recipe names differ, EN recipe name is used."""
        en = "Radish/Radish Salad! Yum."
        zh = "萝卜/萝卜沙拉！好吃。"
        result = self._simulate_cooking_bilingual(en, zh)
        assert result.startswith("Radish/")


class TestRegression:
    """Ensure existing behavior is not broken."""

    def test_bilingualize_pair_preserves_caret(self):
        en = "Welcome^Welcome, sir"
        zh = "欢迎^欢迎，先生"
        expected = "Welcome / 欢迎^Welcome, sir / 欢迎，先生"
        assert bilingualize_pair(en, zh) == expected

    def test_bilingualize_pair_simple(self):
        assert bilingualize_pair("Hello", "你好") == "Hello / 你好"

    def test_bilingualize_pair_empty(self):
        assert bilingualize_pair("Hello", "") == "Hello / "
        assert bilingualize_pair("", "你好") == " / 你好"

    def test_bilingualize_pair_same(self):
        assert bilingualize_pair("Hello", "Hello") == "Hello / Hello"
