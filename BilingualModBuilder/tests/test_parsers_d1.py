import pytest
import sys
sys.path.insert(0, r'C:\Users\minam\code\stardew-bilin\BilingualModBuilder')

from parsers import (
    _bilingualize_d1_segment,
    _bilingualize_segments,
    make_dialogue_bilingual,
    bilingualize_pair,
)


class TestBilingualizeD1Segment:
    """_bilingualize_d1_segment — unit tests for #$1-aware segment bilingualization."""

    def test_simple_k(self):
        en = "#$1 cond#Hello there$k"
        zh = "#$1 cond#你好$k"
        expected = "#$1 cond#Hello there / 你好$k"
        assert _bilingualize_d1_segment(en, zh) == expected

    def test_emotion_before_k(self):
        en = "#$1 cond#Hello there$s$k"
        zh = "#$1 cond#你好$s$k"
        expected = "#$1 cond#Hello there$s / 你好$s$k"
        assert _bilingualize_d1_segment(en, zh) == expected

    def test_emotion_after_k(self):
        en = "#$1 cond#Hello there$k$s"
        zh = "#$1 cond#你好$k$s"
        expected = "#$1 cond#Hello there / 你好$k$s"
        assert _bilingualize_d1_segment(en, zh) == expected

    def test_zero_terminator(self):
        en = "#$1 cond#Hello there$0"
        zh = "#$1 cond#你好$0"
        expected = "#$1 cond#Hello there / 你好$0"
        assert _bilingualize_d1_segment(en, zh) == expected

    def test_with_gender_split(self):
        en = "#$1 cond#Welcome^Welcome, sir$k"
        zh = "#$1 cond#欢迎^欢迎，先生$k"
        expected = "#$1 cond#Welcome / 欢迎^Welcome, sir / 欢迎，先生$k"
        assert _bilingualize_d1_segment(en, zh) == expected

    def test_no_terminator_returns_none(self):
        en = "#$1 cond#Hello there$s"
        zh = "#$1 cond#你好$s"
        assert _bilingualize_d1_segment(en, zh) is None

    def test_no_d1_prefix_returns_none(self):
        en = "Just normal text$s"
        zh = "就是正常文字$s"
        assert _bilingualize_d1_segment(en, zh) is None

    def test_en_has_no_d1_returns_none(self):
        en = "Just normal text"
        zh = "#$1 cond#你好$k"
        assert _bilingualize_d1_segment(en, zh) is None

    def test_zh_has_no_d1_returns_none(self):
        en = "#$1 cond#Hello there$k"
        zh = "只是普通文字"
        assert _bilingualize_d1_segment(en, zh) is None

    def test_zh_no_terminator_returns_none(self):
        en = "#$1 cond#Hello there$k"
        zh = "#$1 cond#你好$s"
        assert _bilingualize_d1_segment(en, zh) is None

    def test_emoji_and_punctuation(self):
        en = "#$1 cond#I'm happy! :D $k"
        zh = "#$1 cond#我好开心！:D $k"
        expected = "#$1 cond#I'm happy! :D  / 我好开心！:D $k"
        assert _bilingualize_d1_segment(en, zh) == expected

    def test_k_is_only_terminator_in_middle(self):
        en = "#$1 cond#Hello $friend$k"
        zh = "#$1 cond#你好 $friend$k"
        expected = "#$1 cond#Hello $friend / 你好 $friend$k"
        result = _bilingualize_d1_segment(en, zh)
        assert result == expected


class TestBilingualizeSegmentsD1:
    """_bilingualize_segments — integration tests with #$1 segments."""

    def test_d1_with_e_sep(self):
        en = "#$1 cond#Hello there$k#$e#How are you?"
        zh = "#$1 cond#你好$k#$e#你好吗？"
        expected = "#$1 cond#Hello there / 你好$k#$e#How are you? / 你好吗？"
        assert _bilingualize_segments(en, zh) == expected

    def test_d1_with_b_sep(self):
        en = "#$1 cond#Hello there$k#$b#And goodbye!"
        zh = "#$1 cond#你好$k#$b#再见！"
        expected = "#$1 cond#Hello there / 你好$k#$b#And goodbye! / 再见！"
        assert _bilingualize_segments(en, zh) == expected

    def test_d1_multi_seg(self):
        en = "#$1 cond#Text A$k#$e#Text B#$e#Text C"
        zh = "#$1 cond#文本A$k#$e#文本B#$e#文本C"
        expected = "#$1 cond#Text A / 文本A$k#$e#Text B / 文本B#$e#Text C / 文本C"
        assert _bilingualize_segments(en, zh) == expected

    def test_d1_with_emotion_multi(self):
        en = "#$1 cond#Text A$s$k#$e#Text B$h"
        zh = "#$1 cond#文本A$s$k#$e#文本B$h"
        expected = "#$1 cond#Text A$s / 文本A$s$k#$e#Text B$h / 文本B$h"
        assert _bilingualize_segments(en, zh) == expected

    def test_pattern_b_unchanged(self):
        en = "#$1 cond#Hello there$s#$e#How are you?"
        zh = "#$1 cond#你好$s#$e#你好吗？"
        expected = "#$1 cond#Hello there$s / #$1 cond#你好$s#$e#How are you? / 你好吗？"
        assert _bilingualize_segments(en, zh) == expected

    def test_no_d1_normal(self):
        en = "Hello there#$e#How are you?"
        zh = "你好#$e#你好吗？"
        expected = "Hello there / 你好#$e#How are you? / 你好吗？"
        assert _bilingualize_segments(en, zh) == expected


class TestMakeDialogueBilingualD1:
    """make_dialogue_bilingual — full integration with real-world #$1 cases."""

    def test_linus_sun(self):
        en = "#$1 linusVandal#Someone was throwing rocks at my tent last night... I just had to wait it out.$s$k#$e#I don't like to stay in one place for too long. There's just too much to experience in the world."
        zh = "#$1 linusVandal#昨天晚上有人朝我的帐篷扔石头……我只能等他们扔完。$s$k#$e#我不喜欢在一个地方呆太长的时间。世界上有太多有意思的事情可以去经历了。"
        expected = "#$1 linusVandal#Someone was throwing rocks at my tent last night... I just had to wait it out.$s / 昨天晚上有人朝我的帐篷扔石头……我只能等他们扔完。$s$k#$e#I don't like to stay in one place for too long. There's just too much to experience in the world. / 我不喜欢在一个地方呆太长的时间。世界上有太多有意思的事情可以去经历了。"
        assert make_dialogue_bilingual(en, zh) == expected

    def test_elliott_thu8(self):
        en = "#$1 elliottApol#It's a little lonely out here on the beach... so I apologize if I was ever a little too forward with you when we first met. I was just eager to have a friend.$k#$e#It feels good to have a close friend like you."
        zh = "#$1 elliottApol#在沙滩上住是有点寂寞……所以初次见面的时候若我哪里显唐突，我先道个歉。我只是想交个朋友才那么亲近罢了。$k#$e#有你这样亲密的好朋友真是太好啦。"
        expected = "#$1 elliottApol#It's a little lonely out here on the beach... so I apologize if I was ever a little too forward with you when we first met. I was just eager to have a friend. / 在沙滩上住是有点寂寞……所以初次见面的时候若我哪里显唐突，我先道个歉。我只是想交个朋友才那么亲近罢了。$k#$e#It feels good to have a close friend like you. / 有你这样亲密的好朋友真是太好啦。"
        assert make_dialogue_bilingual(en, zh) == expected

    def test_haley_sat8(self):
        en = "#$1 haleySeagull#Yesterday I found a seagull with her wing caught in a net. I set her free, of course. She looked so helpless, the poor thing.$k$s#$e#You know, I should probably start exercising more... this youthful metabolism won't last forever."
        zh = "#$1 haleySeagull#昨天我发现一只翅膀被网缠住的海鸥。当然我把它放了。那可怜无助、可怜的样子。$k$s#$e#你知道，我也许真该多运动运动了……这么年轻的新陈代谢不可能维持一辈子的。"
        expected = "#$1 haleySeagull#Yesterday I found a seagull with her wing caught in a net. I set her free, of course. She looked so helpless, the poor thing. / 昨天我发现一只翅膀被网缠住的海鸥。当然我把它放了。那可怜无助、可怜的样子。$k$s#$e#You know, I should probably start exercising more... this youthful metabolism won't last forever. / 你知道，我也许真该多运动运动了……这么年轻的新陈代谢不可能维持一辈子的。"
        assert make_dialogue_bilingual(en, zh) == expected

    def test_pierre_thu8(self):
        en = "#$1 pierre2#Does Abigail look anything like me? Don't tell my wife, but sometimes I wonder if I'm really the father.$k$s#$e#Don't tell my wife, but I hate to cook dinner."
        zh = "#$1 pierre2#阿比盖尔她长得像我吗？别告诉我老婆，不过有时候我真的怀疑我不是她亲爹。$k$s#$e#别跟我老婆说，不过我讨厌做饭。"
        expected = "#$1 pierre2#Does Abigail look anything like me? Don't tell my wife, but sometimes I wonder if I'm really the father. / 阿比盖尔她长得像我吗？别告诉我老婆，不过有时候我真的怀疑我不是她亲爹。$k$s#$e#Don't tell my wife, but I hate to cook dinner. / 别跟我老婆说，不过我讨厌做饭。"
        assert make_dialogue_bilingual(en, zh) == expected

    def test_pam_mon(self):
        en = "#$1 PamDrank#Urghh... my head...$k#$e#You know, I'd eat healthier food if I could afford it.#$e#Hey, you probably have a lot of tasty grub growin' on your farm, hm?"
        zh = "#$1 PamDrank#唔…我的头…$k#$e#如果有钱的话谁不想吃得健康点啊。#$e#对了，你农场里应该有很多好吃的吧，嗯？"
        expected = "#$1 PamDrank#Urghh... my head... / 唔…我的头…$k#$e#You know, I'd eat healthier food if I could afford it. / 如果有钱的话谁不想吃得健康点啊。#$e#Hey, you probably have a lot of tasty grub growin' on your farm, hm? / 对了，你农场里应该有很多好吃的吧，嗯？"
        assert make_dialogue_bilingual(en, zh) == expected

    def test_linus_non_d1_normal(self):
        en = "The crisp air of the wilderness is all I care to know.#$e#I live out here by choice."
        zh = "我想要的就是野外清新的空气。#$e#我住在这外面是我自己的选择。"
        expected = "The crisp air of the wilderness is all I care to know. / 我想要的就是野外清新的空气。#$e#I live out here by choice. / 我住在这外面是我自己的选择。"
        assert make_dialogue_bilingual(en, zh) == expected

    def test_d1_with_nested_dollar(self):
        en = "#$1 cond#I paid $5 for it$k"
        zh = "#$1 cond#我花了5美元$k"
        expected = "#$1 cond#I paid $5 for it / 我花了5美元$k"
        assert make_dialogue_bilingual(en, zh) == expected

    def test_d1_with_game_tokens(self):
        en = "#$1 cond#Hello @! How's %farm?$k"
        zh = "#$1 cond#你好@！%farm怎么样了？$k"
        expected = "#$1 cond#Hello @! How's %farm? / 你好@！%farm怎么样了？$k"
        assert make_dialogue_bilingual(en, zh) == expected
