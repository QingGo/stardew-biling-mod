import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, r'C:\Users\minam\code\stardew-bilin\BilingualModBuilder')

from parsers import (
    BILINGUAL_TEMPLATE,
    bilingualize_pair,
    make_dialogue_bilingual,
)
from build_bilingual_pack import (
    PIPE_BILINGUAL_TEMPLATE,
    asset_path_to_filename,
    is_string_asset,
    is_data_asset,
    is_festival_asset,
)


class TestBilingualTemplateParameters:
    """BILINGUAL_TEMPLATE and PIPE_BILINGUAL_TEMPLATE use generic {left}/{right} keys."""

    def test_template_keys_are_generic(self):
        """Template keys are {left}/{right}, not language-specific."""
        assert BILINGUAL_TEMPLATE == "{left} / {right}"
        assert PIPE_BILINGUAL_TEMPLATE == "{left} | {right}"

    def test_bilingualize_pair_uses_template(self):
        """bilingualize_pair output matches BILINGUAL_TEMPLATE format."""
        result = bilingualize_pair("Hello", "你好")
        assert result == "Hello / 你好"

    def test_bilingualize_pair_reversed_order(self):
        """Swap args → swapped order in output."""
        result = bilingualize_pair("Hallo", "Hello")
        assert result == "Hallo / Hello"

    def test_make_dialogue_bilingual_reversed_order(self):
        """make_dialogue_bilingual with swapped args."""
        result = make_dialogue_bilingual("Hallo", "Hello")
        assert result == "Hallo / Hello"


class TestPairCodeFormat:
    """Pair code format: lang1-lang2 used in When conditions."""

    def test_pair_code_from_spec(self):
        """Pair en:zh → code en-zh."""
        pair = "en:zh"
        lang1, lang2 = pair.split(':')
        pair_code = f"{lang1}-{lang2}"
        assert pair_code == "en-zh"

    def test_various_pair_codes(self):
        """Various language codes produce correct pair codes."""
        tests = [
            ("en:zh", "en-zh"),
            ("de:en", "de-en"),
            ("ja:zh", "ja-zh"),
            ("fr:en", "fr-en"),
        ]
        for pair, expected in tests:
            lang1, lang2 = pair.split(':')
            pair_code = f"{lang1}-{lang2}"
            assert pair_code == expected


class TestBuildScriptFunctions:
    """Key functions in build_bilingual_pack.py remain correct."""

    def test_asset_path_to_filename(self):
        assert asset_path_to_filename("Strings/Objects") == "Strings_Objects.json"
        assert asset_path_to_filename("Data/Events/Town") == "Data_Events_Town.json"

    def test_is_string_asset(self):
        assert is_string_asset("Strings/Objects")
        assert is_string_asset("Characters/Dialogue/Abigail")
        assert is_string_asset("Data/Events/Town")
        assert is_string_asset("Data/TV/CookingChannel")
        assert not is_string_asset("Data/Objects")
        assert not is_string_asset("Data/Festivals/spring13")

    def test_is_data_asset(self):
        assert is_data_asset("Data/Objects")
        assert is_data_asset("Data/hats")
        assert not is_data_asset("Strings/Objects")
        assert not is_data_asset("Data/Events/Town")

    def test_is_festival_asset(self):
        assert is_festival_asset("Data/Festivals/spring13")
        assert not is_festival_asset("Data/Festivals/FestivalDates")
        assert not is_festival_asset("Data/Objects")


class TestContentJsonMultiPair:
    """Verify content.json has correct multi-pair structure."""

    CONTENT_PATH = Path(r'C:\Users\minam\code\stardew-bilin\BilingualMod\content.json')

    def setup_method(self):
        if not self.CONTENT_PATH.exists():
            pytest.skip("content.json not found")

    def test_config_schema_includes_pairs(self):
        """ConfigSchema has AllowValues with pair codes and off."""
        data = json.loads(self.CONTENT_PATH.read_text('utf-8'))
        schema = data['ConfigSchema']['BilingualMode']
        assert 'en-zh' in schema['AllowValues']
        assert 'off' in schema['AllowValues']
        assert 'true' not in schema['AllowValues']

    def test_each_target_has_en_zh_patch(self):
        """At least one patch per target for en-zh mode."""
        data = json.loads(self.CONTENT_PATH.read_text('utf-8'))
        enzh_targets = set()
        true_targets = set()
        for c in data['Changes']:
            mode = c['When'].get('BilingualMode', '')
            if mode == 'en-zh':
                enzh_targets.add(c['Target'])
            if mode == 'true':
                true_targets.add(c['Target'])
        assert len(enzh_targets) > 0
        assert enzh_targets == true_targets

    def test_backward_compat_true_patches_exist(self):
        """Old 'true' config value still matches patches (even though not in AllowValues)."""
        data = json.loads(self.CONTENT_PATH.read_text('utf-8'))
        true_count = sum(1 for c in data['Changes'] if c['When'].get('BilingualMode') == 'true')
        assert true_count > 0

    def test_font_redirect_patches_for_cjk(self):
        """ja-zh pair adds font Load patches for SpriteFont1 and SmallFont."""
        data = json.loads(self.CONTENT_PATH.read_text('utf-8'))
        font_patches = [c for c in data['Changes'] 
                        if c.get('Action') == 'Load' 
                        and 'Fonts/' in c.get('Target', '')
                        and c['When'].get('BilingualMode') == 'ja-zh']
        assert len(font_patches) == 2, f"Expected 2 font patches, got {len(font_patches)}"
        targets = [c['Target'] for c in font_patches]
        assert 'Fonts/SpriteFont1' in targets
        assert 'Fonts/SmallFont' in targets

    def test_event_cs_1726_segment_bilingual(self):
        """Event.cs.1726 has per-segment bilingual format."""
        data = json.loads(self.CONTENT_PATH.read_text('utf-8'))
        for c in data['Changes']:
            if c.get('Target') == 'Strings/StringsFromCSFiles' and c['When'].get('BilingualMode') == 'en-zh':
                val = c['Entries'].get('Event.cs.1726', '')
                segments = val.split('#$b#')
                assert len(segments) == 3
                for seg in segments:
                    assert ' / ' in seg
                return
        assert False, "Event.cs.1726 not found in en-zh patches"
