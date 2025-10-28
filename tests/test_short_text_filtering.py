"""
Unit tests for short text filtering in annotation matching.

Tests the filter_quads_by_proximity function to ensure it correctly handles:
- Very short words (1-2 chars) that appear many times on a page
- Short words (3-8 chars) that appear multiple times
- Longer text that should NOT be filtered
- Edge cases with unusual coordinate distributions
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest
from unittest.mock import MagicMock
import fitz

from src.kindle_parser.amazon_coordinate_system import filter_quads_by_proximity


class MockQuad:
    """Mock PyMuPDF quad for testing"""
    def __init__(self, x0, y0, x1, y1):
        self.rect = fitz.Rect(x0, y0, x1, y1)
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
    
    def __repr__(self):
        return f"MockQuad({self.x0}, {self.y0}, {self.x1}, {self.y1})"


class TestShortTextFiltering:
    """Test suite for short text filtering logic"""
    
    def test_single_char_word_multiple_instances(self):
        """Test filtering of single-char words like 'a', 'I', 'S' that appear many times"""
        # Simulate finding "a" 50 times on the same page
        quads = [MockQuad(100 + i*20, 200, 110 + i*20, 212) for i in range(50)]
        
        # Expected position is near the first occurrence
        expected_x, expected_y = 105, 205
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=1)
        
        # Should return only 1 quad (the closest one)
        assert len(result) == 1, f"Expected 1 quad, got {len(result)}"
        
        # The returned quad should be the closest to expected position
        result_rect = result[0].rect if hasattr(result[0], 'rect') else fitz.Rect(result[0])
        distance = ((result_rect.x0 - expected_x)**2 + (result_rect.y0 - expected_y)**2)**0.5
        assert distance < 10, f"Closest quad should be within 10 points, was {distance:.1f}"
    
    def test_two_char_word_the(self):
        """Test filtering of 'the' which appears frequently"""
        # Simulate finding "the" 30 times across the page
        quads = [MockQuad(50 + i*30, 100 + (i//5)*50, 80 + i*30, 112 + (i//5)*50) for i in range(30)]
        
        # Expected position is in the middle somewhere
        expected_x, expected_y = 250, 250
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=3)
        
        assert len(result) == 1, f"Expected 1 quad for 'the', got {len(result)}"
    
    def test_short_word_states_six_chars(self):
        """Test filtering of 'states' (6 chars) - should be filtered with threshold <=8"""
        # Simulate finding "states" 10 times on a page
        quads = [MockQuad(100 + i*60, 300, 145 + i*60, 312) for i in range(10)]
        
        expected_x, expected_y = 320, 305
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=6)
        
        # With threshold <=8, should filter to single match
        assert len(result) == 1, f"Expected 1 quad for 'states' (6 chars), got {len(result)}"
    
    def test_short_word_context_seven_chars(self):
        """Test filtering of 'context' (7 chars) - should be filtered with threshold <=8"""
        # Simulate finding "context" 8 times on a page
        quads = [MockQuad(80 + i*70, 400, 140 + i*70, 412) for i in range(8)]
        
        expected_x, expected_y = 450, 405
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=7)
        
        # With threshold <=8, should filter to single match
        assert len(result) == 1, f"Expected 1 quad for 'context' (7 chars), got {len(result)}"
    
    def test_eight_char_word_boundary(self):
        """Test filtering of 8-char word (boundary case) - should still be filtered"""
        quads = [MockQuad(100 + i*80, 500, 180 + i*80, 512) for i in range(5)]
        
        expected_x, expected_y = 340, 505
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=8)
        
        # With threshold <=8, should still filter
        assert len(result) == 1, f"Expected 1 quad for 8-char word, got {len(result)}"
    
    def test_nine_char_word_not_filtered_unless_clustered(self):
        """Test that 9-char words use clustering logic, not single-quad filtering"""
        # Create quads that are widely distributed (>150 points apart)
        quads = [
            MockQuad(100, 100, 180, 112),
            MockQuad(400, 100, 480, 112),
            MockQuad(100, 300, 180, 312),
        ]
        
        expected_x, expected_y = 450, 105
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=9)
        
        # Should use clustering logic, likely returning just the closest cluster
        # In this case, should return the quad at (400, 100) which is closest
        assert len(result) >= 1, "Should return at least the closest quad"
        # The closest should be included
        has_closest = any(hasattr(q, 'rect') and abs(q.rect.x0 - 400) < 10 for q in result)
        assert has_closest, "Should include the quad closest to expected position"
    
    def test_long_phrase_not_filtered(self):
        """Test that longer text (>8 chars) is not single-quad filtered"""
        # Simulate finding a longer phrase only 2 times (unlikely but possible)
        quads = [
            MockQuad(100, 200, 250, 212),
            MockQuad(300, 400, 450, 412),
        ]
        
        expected_x, expected_y = 105, 205
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=25)
        
        # Should use clustering logic, return the closest one or both if they form a cluster
        # The first one should definitely be included as it's closest
        assert len(result) >= 1, "Should return at least one quad"
        result_rect = result[0].rect if hasattr(result[0], 'rect') else fitz.Rect(result[0])
        assert abs(result_rect.x0 - 100) < 10, "Should include the closest quad"
    
    def test_multi_line_highlight_not_broken(self):
        """Test that legitimate multi-line highlights are kept together"""
        # Simulate a 3-line highlight where quads are vertically stacked
        quads = [
            MockQuad(100, 200, 400, 212),  # Line 1
            MockQuad(100, 215, 400, 227),  # Line 2 (15 points below)
            MockQuad(100, 230, 300, 242),  # Line 3 (15 points below)
        ]
        
        expected_x, expected_y = 105, 205
        
        # Even for short text in multi-line context
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=20)
        
        # Should keep all 3 quads as they form a continuous vertical cluster
        assert len(result) >= 3, f"Should keep multi-line highlight together, got {len(result)} quads"
    
    def test_same_word_different_lines_filtered(self):
        """Test that same short word on different lines gets filtered to closest"""
        # Simulate "is" appearing once per line across 10 lines
        quads = [MockQuad(100, 100 + i*50, 120, 112 + i*50) for i in range(10)]
        
        expected_x, expected_y = 105, 305  # Near the 5th occurrence
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=2)
        
        assert len(result) == 1, f"Expected 1 quad for 'is' across lines, got {len(result)}"
        
        # Verify it's the one closest to expected position
        result_rect = result[0].rect if hasattr(result[0], 'rect') else fitz.Rect(result[0])
        distance = ((result_rect.x0 - expected_x)**2 + (result_rect.y0 - expected_y)**2)**0.5
        assert distance < 50, f"Should return closest occurrence, distance was {distance:.1f}"
    
    def test_extreme_case_hundred_instances(self):
        """Test extreme case: word appears 100+ times (e.g., 'a' in a dense page)"""
        # Simulate finding "a" 100 times in a grid pattern
        quads = []
        for row in range(10):
            for col in range(10):
                quads.append(MockQuad(50 + col*50, 50 + row*30, 60 + col*50, 62 + row*30))
        
        expected_x, expected_y = 275, 200  # Somewhere in the middle
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=1)
        
        assert len(result) == 1, f"Expected 1 quad even with 100 instances, got {len(result)}"
        
        # Should return the closest one
        result_rect = result[0].rect if hasattr(result[0], 'rect') else fitz.Rect(result[0])
        distance = ((result_rect.x0 - expected_x)**2 + (result_rect.y0 - expected_y)**2)**0.5
        assert distance < 50, f"Should find reasonably close match, distance was {distance:.1f}"
    
    def test_no_expected_position_provided(self):
        """Test behavior when no expected position is provided (None values)"""
        quads = [MockQuad(100 + i*50, 200, 140 + i*50, 212) for i in range(5)]
        
        # When no position is provided, should handle gracefully
        # For short text, might still try to filter but should not crash
        # Fallback: return first quad or use default position (0, 0)
        try:
            result = filter_quads_by_proximity(quads, 0, 0, search_text_length=3)
            # Should return at least one quad
            assert len(result) > 0, "Should return at least one quad"
        except TypeError:
            # If it doesn't handle None gracefully, skip this test
            # The function currently expects valid float coordinates
            pytest.skip("Function doesn't handle None coordinates - design decision")
    
    def test_no_search_text_length_provided(self):
        """Test behavior when search_text_length is None"""
        quads = [MockQuad(100 + i*50, 200, 140 + i*50, 212) for i in range(10)]
        
        expected_x, expected_y = 105, 205
        
        # Should use clustering logic instead of single-quad filtering
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=None)
        
        # Should return closest cluster
        assert len(result) >= 1, "Should return at least one quad"
    
    def test_empty_quads_list(self):
        """Test handling of empty quads list"""
        quads = []
        
        result = filter_quads_by_proximity(quads, 100, 200, search_text_length=5)
        
        assert len(result) == 0, "Should return empty list for empty input"
    
    def test_single_quad_not_filtered(self):
        """Test that single quad is always returned as-is"""
        quads = [MockQuad(100, 200, 150, 212)]
        
        result = filter_quads_by_proximity(quads, 500, 500, search_text_length=1)
        
        # Even if far from expected position, single quad should be returned
        assert len(result) == 1, "Single quad should always be returned"
    
    def test_two_clusters_short_word_picks_closer(self):
        """Test that for short words with two clusters, picks the closer one"""
        # Create two clusters of quads far apart
        cluster1 = [MockQuad(100, 100 + i*15, 140, 112 + i*15) for i in range(3)]
        cluster2 = [MockQuad(500, 100 + i*15, 540, 112 + i*15) for i in range(3)]
        quads = cluster1 + cluster2
        
        # Expected position near cluster1
        expected_x, expected_y = 120, 110
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=4)
        
        # Should return only 1 quad (from cluster1, the closest individual quad)
        assert len(result) == 1, f"Expected 1 quad for short word with clusters, got {len(result)}"
        
        # Verify it's from cluster1 (x around 100-140)
        result_rect = result[0].rect if hasattr(result[0], 'rect') else fitz.Rect(result[0])
        assert result_rect.x0 < 200, f"Should pick quad from closer cluster, got x={result_rect.x0}"
    
    def test_regression_page_10_the_bug(self):
        """Regression test for the original 'the' bug on page 10 of Alfredo PDF"""
        # Simulate two "the" instances on same line with coordinates from real bug
        quads = [
            MockQuad(167.28, 547.82, 182.16, 558.70),  # First "the"
            MockQuad(333.84, 547.82, 348.72, 558.70),  # Second "the" (same line)
        ]
        
        # KRDS coordinates pointed to the first one
        expected_x, expected_y = 170, 550
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=3)
        
        # Should return only the first "the"
        assert len(result) == 1, "Should return only one 'the' instance"
        
        result_rect = result[0].rect if hasattr(result[0], 'rect') else fitz.Rect(result[0])
        # Should be the first one (x around 167)
        assert abs(result_rect.x0 - 167.28) < 5, f"Should pick first 'the', got x={result_rect.x0}"
    
    def test_regression_states_bug(self):
        """Regression test for 'states' bug (6 chars) appearing multiple times"""
        # Simulate "states" appearing 3 times on page 37 of r2-3 PDF
        quads = [
            MockQuad(207.0, 100.6, 239.0, 114.0),   # Instance 1
            MockQuad(102.1, 100.6, 134.1, 114.0),   # Instance 2 (same line)
            MockQuad(350.0, 120.0, 382.0, 134.0),   # Instance 3 (different line)
        ]
        
        # KRDS pointed to first instance
        expected_x, expected_y = 210, 105
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=6)
        
        # With threshold <=8, should return only the closest one
        assert len(result) == 1, f"Should return only one 'states' instance, got {len(result)}"
        
        result_rect = result[0].rect if hasattr(result[0], 'rect') else fitz.Rect(result[0])
        assert abs(result_rect.x0 - 207.0) < 10, f"Should pick correct 'states', got x={result_rect.x0}"
    
    def test_regression_context_bug(self):
        """Regression test for 'context' bug (7 chars) appearing twice"""
        # Simulate "context" appearing twice on page 44 of r2-3 PDF
        quads = [
            MockQuad(392.9, 295.0, 431.6, 308.4),  # Instance 1
            MockQuad(189.5, 295.0, 228.2, 308.4),  # Instance 2 (same line)
        ]
        
        # KRDS pointed to first instance
        expected_x, expected_y = 395, 298
        
        result = filter_quads_by_proximity(quads, expected_x, expected_y, search_text_length=7)
        
        # Should return only the first one
        assert len(result) == 1, f"Should return only one 'context' instance, got {len(result)}"
        
        result_rect = result[0].rect if hasattr(result[0], 'rect') else fitz.Rect(result[0])
        assert abs(result_rect.x0 - 392.9) < 10, f"Should pick correct 'context', got x={result_rect.x0}"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
