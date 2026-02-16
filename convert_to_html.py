"""
Simple Markdown to HTML converter for USER_GUIDE.md
"""

import re
from pathlib import Path

def create_id(text):
    """Create a URL-friendly ID from text"""
    # Remove emojis and special characters
    text = re.sub(r'[^\w\s-]', '', text)
    # Convert to lowercase and replace spaces with hyphens
    return text.strip().lower().replace(' ', '-')

def md_to_html(md_content):
    """Convert markdown to HTML with basic formatting"""
    html = md_content
    
    # Headers with IDs for anchor links
    def h1_replace(match):
        text = match.group(1)
        id_attr = create_id(text)
        return f'<h1 id="{id_attr}">{text}</h1>'
    
    def h2_replace(match):
        text = match.group(1)
        id_attr = create_id(text)
        return f'<h2 id="{id_attr}">{text}</h2>'
    
    def h3_replace(match):
        text = match.group(1)
        id_attr = create_id(text)
        return f'<h3 id="{id_attr}">{text}</h3>'
    
    def h4_replace(match):
        text = match.group(1)
        id_attr = create_id(text)
        return f'<h4 id="{id_attr}">{text}</h4>'
    
    html = re.sub(r'^# (.+)$', h1_replace, html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', h2_replace, html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', h3_replace, html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.+)$', h4_replace, html, flags=re.MULTILINE)
    
    # Bold
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    
    # Italic
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    
    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # Code blocks
    html = re.sub(r'```(\w+)?\n(.*?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
    
    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)
    
    # Unordered lists
    lines = html.split('\n')
    in_list = False
    result = []
    for line in lines:
        if re.match(r'^- ', line):
            if not in_list:
                result.append('<ul>')
                in_list = True
            result.append(f'<li>{line[2:]}</li>')
        elif re.match(r'^\d+\. ', line):
            if not in_list:
                result.append('<ol>')
                in_list = 'ol'
            result.append(f'<li>{re.sub(r"^\d+\. ", "", line)}</li>')
        else:
            if in_list == True:
                result.append('</ul>')
                in_list = False
            elif in_list == 'ol':
                result.append('</ol>')
                in_list = False
            result.append(line)
    
    if in_list == True:
        result.append('</ul>')
    elif in_list == 'ol':
        result.append('</ol>')
    
    html = '\n'.join(result)
    
    # Paragraphs
    html = re.sub(r'\n\n', r'</p><p>', html)
    html = '<p>' + html + '</p>'
    
    # Clean up empty paragraphs
    html = re.sub(r'<p>\s*</p>', '', html)
    html = re.sub(r'<p>(<h[1-6]>)', r'\1', html)
    html = re.sub(r'(</h[1-6]>)</p>', r'\1', html)
    html = re.sub(r'<p>(<pre>)', r'\1', html)
    html = re.sub(r'(</pre>)</p>', r'\1', html)
    html = re.sub(r'<p>(<ul>)', r'\1', html)
    html = re.sub(r'(</ul>)</p>', r'\1', html)
    html = re.sub(r'<p>(<ol>)', r'\1', html)
    html = re.sub(r'(</ol>)</p>', r'\1', html)
    
    return html

def create_html():
    """Create HTML file from USER_GUIDE.md"""
    md_path = Path('USER_GUIDE.md')
    html_path = Path('USER_GUIDE.html')
    
    # Read markdown
    md_content = md_path.read_text(encoding='utf-8')
    
    # Convert to HTML
    body_html = md_to_html(md_content)
    
    # HTML template
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PBIP Studio - User Guide</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #ffffff;
            color: #333;
        }}
        
        h1 {{
            color: #0078D4;
            border-bottom: 3px solid #0078D4;
            padding-bottom: 10px;
            margin-top: 30px;
        }}
        
        h2 {{
            color: #0078D4;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 8px;
            margin-top: 30px;
        }}
        
        h3 {{
            color: #106EBE;
            margin-top: 25px;
        }}
        
        h4 {{
            color: #1E88E5;
            margin-top: 20px;
        }}
        
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 90%;
            color: #c7254e;
        }}
        
        pre {{
            background: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border-left: 4px solid #0078D4;
            margin: 15px 0;
        }}
        
        pre code {{
            background: none;
            padding: 0;
            color: #333;
            font-size: 14px;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        
        th {{
            background: #0078D4;
            color: white;
            font-weight: 600;
        }}
        
        tr:nth-child(even) {{
            background: #f9f9f9;
        }}
        
        tr:hover {{
            background: #f0f7ff;
        }}
        
        a {{
            color: #0078D4;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        ul, ol {{
            margin: 10px 0;
            padding-left: 30px;
        }}
        
        li {{
            margin: 8px 0;
        }}
        
        strong {{
            font-weight: 600;
            color: #000;
        }}
        
        em {{
            font-style: italic;
            color: #555;
        }}
        
        blockquote {{
            border-left: 4px solid #0078D4;
            margin: 15px 0;
            padding-left: 15px;
            color: #666;
            font-style: italic;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #e0e0e0;
            margin: 30px 0;
        }}
        
        .toc {{
            background: #f8f8f8;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        
        @media print {{
            body {{
                max-width: 100%;
                padding: 10px;
            }}
            
            pre {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    {body_html}
</body>
</html>"""
    
    # Write HTML file
    html_path.write_text(html_template, encoding='utf-8')
    print(f"✓ Created {html_path}")

if __name__ == '__main__':
    create_html()
