#!/usr/bin/env python3
"""
SARVAYA Build Script — Minifies CSS, JS, and HTML into dist/
Run: python build.py

Uses only Python stdlib. No dependencies required.
"""
import os
import re
import shutil

SRC = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(SRC, 'dist')

SKIP_DIRS = {'dist', 'node_modules', '.git', '__pycache__'}
SKIP_FILES = {'build.py'}


def minify_css(content):
    """Remove comments, collapse whitespace, strip unnecessary chars."""
    content = re.sub(r'/\*[\s\S]*?\*/', '', content)          # block comments
    content = re.sub(r'\s+', ' ', content)                     # collapse whitespace
    content = re.sub(r'\s*([{}:;,>~+])\s*', r'\1', content)   # around punctuation
    content = re.sub(r';}', '}', content)                      # trailing semicolons
    content = re.sub(r'^\s+', '', content)                     # leading whitespace
    return content.strip()


def minify_js(content):
    """Remove comments and blank lines. Preserves string contents."""
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)   # line comments
    content = re.sub(r'/\*[\s\S]*?\*/', '', content)               # block comments
    lines = [line.rstrip() for line in content.split('\n') if line.strip()]
    return '\n'.join(lines)


def minify_html(content):
    """Collapse whitespace between tags, remove HTML comments."""
    # Remove comments (but not conditional IE comments)
    content = re.sub(r'<!--(?!\[).*?-->', '', content, flags=re.DOTALL)
    # Collapse whitespace between tags
    content = re.sub(r'>\s+<', '> <', content)
    # Remove blank lines
    content = re.sub(r'\n\s*\n', '\n', content)
    return content.strip()


def format_size(size):
    """Format bytes to human-readable."""
    if size < 1024:
        return f'{size}B'
    return f'{size / 1024:.1f}KB'


def main():
    # Clean dist
    if os.path.exists(DIST):
        shutil.rmtree(DIST)

    total_original = 0
    total_minified = 0
    file_count = 0

    print('=' * 60)
    print('SARVAYA Build — Minifying to dist/')
    print('=' * 60)

    for root, dirs, files in os.walk(SRC):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for filename in files:
            if filename in SKIP_FILES:
                continue

            src_path = os.path.join(root, filename)
            rel_path = os.path.relpath(src_path, SRC)
            dst_path = os.path.join(DIST, rel_path)

            os.makedirs(os.path.dirname(dst_path), exist_ok=True)

            ext = os.path.splitext(filename)[1].lower()

            if ext == '.css':
                with open(src_path, 'r', encoding='utf-8') as f:
                    original = f.read()
                minified = minify_css(original)
                with open(dst_path, 'w', encoding='utf-8') as f:
                    f.write(minified)

                orig_size = len(original.encode('utf-8'))
                mini_size = len(minified.encode('utf-8'))
                savings = (1 - mini_size / orig_size) * 100 if orig_size > 0 else 0
                print(f'  CSS  {rel_path:<40} {format_size(orig_size):>8} -> {format_size(mini_size):>8}  ({savings:.0f}% smaller)')
                total_original += orig_size
                total_minified += mini_size
                file_count += 1

            elif ext == '.js':
                with open(src_path, 'r', encoding='utf-8') as f:
                    original = f.read()
                minified = minify_js(original)
                with open(dst_path, 'w', encoding='utf-8') as f:
                    f.write(minified)

                orig_size = len(original.encode('utf-8'))
                mini_size = len(minified.encode('utf-8'))
                savings = (1 - mini_size / orig_size) * 100 if orig_size > 0 else 0
                print(f'  JS   {rel_path:<40} {format_size(orig_size):>8} -> {format_size(mini_size):>8}  ({savings:.0f}% smaller)')
                total_original += orig_size
                total_minified += mini_size
                file_count += 1

            elif ext == '.html':
                with open(src_path, 'r', encoding='utf-8') as f:
                    original = f.read()
                minified = minify_html(original)
                with open(dst_path, 'w', encoding='utf-8') as f:
                    f.write(minified)

                orig_size = len(original.encode('utf-8'))
                mini_size = len(minified.encode('utf-8'))
                savings = (1 - mini_size / orig_size) * 100 if orig_size > 0 else 0
                print(f'  HTML {rel_path:<40} {format_size(orig_size):>8} -> {format_size(mini_size):>8}  ({savings:.0f}% smaller)')
                total_original += orig_size
                total_minified += mini_size
                file_count += 1

            else:
                # Copy as-is (images, json, xml, txt, svg, etc.)
                shutil.copy2(src_path, dst_path)

    print('=' * 60)
    total_savings = (1 - total_minified / total_original) * 100 if total_original > 0 else 0
    print(f'  TOTAL: {file_count} files minified')
    print(f'  {format_size(total_original)} -> {format_size(total_minified)}  ({total_savings:.1f}% smaller)')
    print(f'  Output: {DIST}')
    print('=' * 60)


if __name__ == '__main__':
    main()
