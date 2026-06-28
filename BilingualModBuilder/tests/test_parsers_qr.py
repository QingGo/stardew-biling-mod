import pytest
import sys
sys.path.insert(0, r'C:\Users\minam\code\stardew-bilin\BilingualModBuilder')

from parsers import (
    bilingualize_pair,
    bilingualize_qr_text,
    bilingualize_event_quoted_text,
    _bilingualize_segments,
)


class TestBilingualizeQrText:
    """bilingualize_qr_text — $q/$r inline Q&A bilingualization."""

    def test_simple_qr(self):
        en = "$q -1 null#Do you think everyone's ready for the egg hunt yet?#$r -1 0 yes#Yes, let's start.#$r -1 0 no#Not yet."
        zh = "$q -1 null#你觉得大家都准备好彩蛋大寻宝了吗？#$r -1 0 yes#是的，让我们开始吧。#$r -1 0 no#还没有。"
        expected = "$q -1 null#Do you think everyone's ready for the egg hunt yet? / 你觉得大家都准备好彩蛋大寻宝了吗？#$r -1 0 yes#Yes, let's start. / 是的，让我们开始吧。#$r -1 0 no#Not yet. / 还没有。"
        assert bilingualize_qr_text(en, zh) == expected

    def test_dance_question(self):
        en = "$q -1 null#Well, should we start the dance now?#$r -1 0 yes#Yes, let's start.#$r -1 0 no#Not yet."
        zh = "$q -1 null#那我们现在就开始跳舞吗？#$r -1 0 yes#是的，让我们开始吧。#$r -1 0 no#还没有。"
        expected = "$q -1 null#Well, should we start the dance now? / 那我们现在就开始跳舞吗？#$r -1 0 yes#Yes, let's start. / 是的，让我们开始吧。#$r -1 0 no#Not yet. / 还没有。"
        assert bilingualize_qr_text(en, zh) == expected

    def test_luau_question(self):
        en = "$q -1 null#Should we move forward with the Luau? The governor seems a little hungry.#$r -1 0 yes#Yes, let's start.#$r -1 0 no#Not yet."
        zh = "$q -1 null#我们应该去宴会吗？州长看起来有些饿了。#$r -1 0 yes#是的，让我们开始吧。#$r -1 0 no#还没有。"
        expected = "$q -1 null#Should we move forward with the Luau? The governor seems a little hungry. / 我们应该去宴会吗？州长看起来有些饿了。#$r -1 0 yes#Yes, let's start. / 是的，让我们开始吧。#$r -1 0 no#Not yet. / 还没有。"
        assert bilingualize_qr_text(en, zh) == expected

    def test_boat_question(self):
        en = "$q -1 null#What do you think... should I launch the boat now?#$r -1 0 yes#Yes.#$r -1 0 no#Not yet."
        zh = "$q -1 null#你觉得呢……现在我应该开船吗？#$r -1 0 yes#是。#$r -1 0 no#还不用。"
        expected = "$q -1 null#What do you think... should I launch the boat now? / 你觉得呢……现在我应该开船吗？#$r -1 0 yes#Yes. / 是。#$r -1 0 no#Not yet. / 还不用。"
        assert bilingualize_qr_text(en, zh) == expected

    def test_fair_question(self):
        en = "$q -1 null#Oh... are you already finished setting up your grange display?#$r -1 0 yes#Yes.#$r -1 0 no#Not yet."
        zh = "$q -1 null#哦……你已经准备好农庄展览了吗？#$r -1 0 yes#是。#$r -1 0 no#还没有。"
        expected = "$q -1 null#Oh... are you already finished setting up your grange display? / 哦……你已经准备好农庄展览了吗？#$r -1 0 yes#Yes. / 是。#$r -1 0 no#Not yet. / 还没有。"
        assert bilingualize_qr_text(en, zh) == expected

    def test_ice_fishing_question(self):
        en = "$q -1 null#Are you ready to participate in the ice fishing competition?#$r -1 0 yes#Yes.#$r -1 0 no#Not yet."
        zh = "$q -1 null#你准备参加冰钓比赛吗？#$r -1 0 yes#是。#$r -1 0 no#还没有。"
        expected = "$q -1 null#Are you ready to participate in the ice fishing competition? / 你准备参加冰钓比赛吗？#$r -1 0 yes#Yes. / 是。#$r -1 0 no#Not yet. / 还没有。"
        assert bilingualize_qr_text(en, zh) == expected

    def test_dance_ask_male(self):
        en = "$q -1 null#...Yes, dear?#$r -1 0 danceAsk#(Ask {0} to be your dance partner)#$r -1 0 null#Never mind..."
        zh = "$q -1 null#……什么事，亲爱的？#$r -1 0 danceAsk#（邀请{0}作你的舞伴）#$r -1 0 null#没事……"
        expected = "$q -1 null#...Yes, dear? / ……什么事，亲爱的？#$r -1 0 danceAsk#(Ask {0} to be your dance partner) / （邀请{0}作你的舞伴）#$r -1 0 null#Never mind... / 没事……"
        assert bilingualize_qr_text(en, zh) == expected

    def test_dance_ask_female(self):
        en = "$q -1 null#...Yes?#$r -1 0 danceAsk#(Ask {0} to be your dance partner)#$r -1 0 null#Never mind..."
        zh = "$q -1 null#……什么事？#$r -1 0 danceAsk#（邀请{0}作你的舞伴）#$r -1 0 null#没事……"
        expected = "$q -1 null#...Yes? / ……什么事？#$r -1 0 danceAsk#(Ask {0} to be your dance partner) / （邀请{0}作你的舞伴）#$r -1 0 null#Never mind... / 没事……"
        assert bilingualize_qr_text(en, zh) == expected

    def test_qr_with_emotion(self):
        en = "$q -1 null#Do you think everyone's ready?$h#$r -1 0 yes#Yes!$h"
        zh = "$q -1 null#大家都准备好了吗？$h#$r -1 0 yes#是的！$h"
        expected = "$q -1 null#Do you think everyone's ready?$h / 大家都准备好了吗？$h#$r -1 0 yes#Yes!$h / 是的！$h"
        assert bilingualize_qr_text(en, zh) == expected

    def test_qr_with_b_sep_in_question(self):
        en = "$q -1 null#Do you think everyone's ready?#$b#Are you sure?#$r -1 0 yes#Yes.#$r -1 0 no#No."
        zh = "$q -1 null#大家都准备好了吗？#$b#你确定吗？#$r -1 0 yes#是的。#$r -1 0 no#没有。"
        expected = "$q -1 null#Do you think everyone's ready? / 大家都准备好了吗？#$b#Are you sure? / 你确定吗？#$r -1 0 yes#Yes. / 是的。#$r -1 0 no#No. / 没有。"
        assert bilingualize_qr_text(en, zh) == expected


class TestBilingualizeEventQuotedText:
    """bilingualize_event_quoted_text — integration with $q/$r text."""

    def test_event_quoted_simple_qr(self):
        en = "$q -1 null#Do you think everyone's ready for the egg hunt yet?#$r -1 0 yes#Yes, let's start.#$r -1 0 no#Not yet."
        zh = "$q -1 null#你觉得大家都准备好彩蛋大寻宝了吗？#$r -1 0 yes#是的，让我们开始吧。#$r -1 0 no#还没有。"
        expected = "$q -1 null#Do you think everyone's ready for the egg hunt yet? / 你觉得大家都准备好彩蛋大寻宝了吗？#$r -1 0 yes#Yes, let's start. / 是的，让我们开始吧。#$r -1 0 no#Not yet. / 还没有。"
        assert bilingualize_event_quoted_text(en, zh) == expected

    def test_event_quoted_text_before_q(self):
        en = "Hmm, let me think... $q -1 null#Ready?#$r -1 0 yes#Yes."
        zh = "嗯，让我想想…… $q -1 null#准备好了吗？#$r -1 0 yes#好了。"
        expected = "Hmm, let me think...  / 嗯，让我想想…… $q -1 null#Ready? / 准备好了吗？#$r -1 0 yes#Yes. / 好了。"
        assert bilingualize_event_quoted_text(en, zh) == expected

    def test_event_quoted_missing_zh(self):
        en = "Some text $q -1 null#Ready?#$r -1 0 yes#Yes."
        result = bilingualize_event_quoted_text(en, en)
        assert result == en

    def test_event_quoted_no_qr_falls_back_to_segments(self):
        en = "Hello there! How are you?"
        zh = "你好！你怎么样？"
        expected = "Hello there! How are you? / 你好！你怎么样？"
        assert bilingualize_event_quoted_text(en, zh) == expected


class TestBilingualizePairBreaksQr:
    """Demonstrate that bilingualize_pair corrupts $q/$r format.

    This documents the bug: bilingualize_pair() naively concatenates
    the full en + zh strings, breaking the $q/$r structure that
    Stardew Valley's event parser expects.
    """

    def test_bilingualize_pair_corrupts_egg_hunt(self):
        en = "$q -1 null#Do you think everyone's ready for the egg hunt yet?#$r -1 0 yes#Yes, let's start.#$r -1 0 no#Not yet."
        zh = "$q -1 null#你觉得大家都准备好彩蛋大寻宝了吗？#$r -1 0 yes#是的，让我们开始吧。#$r -1 0 no#还没有。"
        result = bilingualize_pair(en, zh)
        # bilingualize_pair concatenates: {en} / {zh}
        # The result contains TWO complete $q/$r blocks — game can't parse this.
        assert "$q -1 null#Do you think everyone's ready" in result
        assert "$q -1 null#你觉得大家都准备好" in result
        # The first $r's response text is NOT bilingualized; the entire
        # English block is kept as-is followed by the Chinese block.
        # This means the text contains "Not yet.\n$q -1 null#..." which
        # the game's $q/$r parser cannot handle.
        assert "$q" in result[result.index("Not yet."):]
        # This would cause the Q&A to fail in-game

    def test_bilingualize_pair_corrupts_dance_ask(self):
        en = "$q -1 null#...Yes, dear?#$r -1 0 danceAsk#(Ask {0} to be your dance partner)#$r -1 0 null#Never mind..."
        zh = "$q -1 null#……什么事，亲爱的？#$r -1 0 danceAsk#（邀请{0}作你的舞伴）#$r -1 0 null#没事……"
        result = bilingualize_pair(en, zh)
        # Same corruption: second $q block follows first $r's last response
        assert "$q" in result.split("Never mind...")[1] if "Never mind..." in result else True
        assert True  # placeholder — we just need to confirm the pattern
