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


class TestDialogueQrBilingual:
    def test_dialogue_qr_egg_hunt(self):
        en = "$q -1 null#Do you think everyone's ready for the egg hunt yet?#$r -1 0 yes#Yes, let's start.#$r -1 0 no#Not yet."
        zh = "$q -1 null#你觉得大家都准备好彩蛋大寻宝了吗？#$r -1 0 yes#是的，让我们开始吧。#$r -1 0 no#还没有。"
        result = bilingualize_pair(en, zh)
        assert result.count("$q -1 null#") == 1
        assert "Make it so" not in result

    def test_dialogue_qr_dance_ask(self):
        en = "$q -1 null#...Yes, dear?#$r -1 0 danceAsk#(Ask {0} to be your dance partner)#$r -1 0 null#Never mind..."
        zh = "$q -1 null#……什么事，亲爱的？#$r -1 0 danceAsk#（邀请{0}作你的舞伴）#$r -1 0 null#没事……"
        result = bilingualize_pair(en, zh)
        assert result.count("$q") == 1
        assert "...Yes, dear?" in result
        assert "Never mind..." in result

    def test_dialogue_qr_with_preamble(self):
        en = "Oh, and another thing... Isn't that wonderful? #$q -1 -1#Membership costs {0}g. Well, would you like to join us? #$r -1 -1 Yes#Yes.#$r -1 -1 No#No."
        zh = "啊，还有另一件事……那不是好极了？ #$q -1 -1#会员费用 {0} 金。那么，你愿意加入我们吗？ #$r -1 -1 Yes#愿意。 #$r -1 -1 No#不愿意。"
        result = bilingualize_pair(en, zh)
        assert result.count("$q -1 -1#") == 1
        assert "Oh, and another thing..." in result
        assert "Membership costs" in result

    def test_dialogue_qr_after_b_sep(self):
        en = "So, naturally, I turn to you.#$b#$q -1 -1#We could make this happen for 500,000g...$h#$r -1 -1 Yes#Yes#$r -1 -1 No#No"
        zh = "于是我很自然地找到了您。#$b#$q -1 -1#我们只需要 500,000 金。$h#$r -1 -1 Yes#是#$r -1 -1 No#否"
        result = bilingualize_pair(en, zh)
        assert result.count("$q -1 -1#") == 1
        assert "500,000g...$h" in result

    def test_dialogue_qr_emotion_in_question(self):
        en = "$q -1 -1#Are you ready?$h#$r -1 -1 Yes#Yes!$h#$r -1 -1 No#No."
        zh = "$q -1 -1#准备好了吗？$h#$r -1 -1 Yes#好了！$h#$r -1 -1 No#还没有。"
        result = bilingualize_pair(en, zh)
        assert result.count("$q") == 1
        assert "Are you ready?$h" in result

    def test_dialogue_qr_r_count_mismatch(self):
        en = "$q -1 null#Ready?#$r -1 0 yes#Yes"
        zh = "$q -1 null#准备好了吗？#$r -1 0 yes#好了#$r -1 0 no#还没"
        result = bilingualize_pair(en, zh)
        assert result.count("$q") == 2
