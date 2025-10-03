#!/usr/bin/env python3
"""
Verify the snake highlight pattern in generated PDFs
"""
import fitz
import sys

def check_snake_pattern(pdf_path: str):
    """Check if highlights follow snake pattern"""
    print(f"🔍 Checking snake pattern in: {pdf_path}")
    print("="*70)
    
    doc = fitz.open(pdf_path)
    
    for page_num in range(min(5, len(doc))):  # Check first 5 pages
        page = doc[page_num]
        annots = list(page.annots())
        highlights = [a for a in annots if a.type[1] == "Highlight"]
        
        if not highlights:
            continue
            
        print(f"\n📄 Page {page_num + 1}: {len(highlights)} highlight(s)")
        
        for i, hl in enumerate(highlights):
            vertices = hl.vertices
            if not vertices:
                continue
                
            quad_count = len(vertices) // 4
            print(f"\n   Highlight {i+1}: {quad_count} quads")
            
            # Get highlight content from info
            content = hl.info.get("content", "")
            if content:
                preview = content[:50] + "..." if len(content) > 50 else content
                print(f"   Content: \"{preview}\"")
            
            # Analyze quad pattern
            quads = []
            for j in range(0, len(vertices), 4):
                quad_points = vertices[j:j+4]
                x_coords = [p[0] for p in quad_points]
                y_coords = [p[1] for p in quad_points]
                quads.append({
                    'left': min(x_coords),
                    'right': max(x_coords),
                    'top': min(y_coords),
                    'bottom': max(y_coords),
                    'width': max(x_coords) - min(x_coords)
                })
            
            # Sort quads by vertical position
            quads.sort(key=lambda q: q['top'])
            
            if quad_count == 1:
                print(f"   ✓ Single-line highlight")
                print(f"     Width: {quads[0]['width']:.1f}pt")
            elif quad_count > 1:
                print(f"   ✓ Multi-line snake pattern:")
                for j, quad in enumerate(quads):
                    line_type = "first" if j == 0 else ("last" if j == quad_count-1 else "middle")
                    print(f"     Line {j+1} ({line_type}): left={quad['left']:.1f}, right={quad['right']:.1f}, width={quad['width']:.1f}pt")
                
                # Verify snake pattern
                if quad_count >= 3:
                    # Middle lines should have consistent left/right margins
                    middle_lefts = [quads[j]['left'] for j in range(1, quad_count-1)]
                    middle_rights = [quads[j]['right'] for j in range(1, quad_count-1)]
                    
                    if middle_lefts and middle_rights:
                        left_variation = max(middle_lefts) - min(middle_lefts)
                        right_variation = max(middle_rights) - min(middle_rights)
                        
                        if left_variation < 5 and right_variation < 5:
                            print(f"   ✅ Perfect snake: middle lines aligned (left_var={left_variation:.1f}, right_var={right_variation:.1f})")
                        else:
                            print(f"   ⚠️  Snake variation: left_var={left_variation:.1f}, right_var={right_variation:.1f}")
    
    doc.close()
    print(f"\n{'='*70}")
    print("✅ Snake pattern verification complete")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_snake_pattern(sys.argv[1])
    else:
        # Default test file
        check_snake_pattern("tests/output/highlight_width_test.pdf")
