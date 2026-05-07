#!/usr/bin/env python3
"""
Update the results index.html with a pass/fail row for the current run.

Usage: checkresults.py <TAU_BRANCH>

Must be run from within the dated results directory (e.g. results/2026-03-26_14-54/).
The index.html is expected one level up.

Prints "found an error!" to stdout if errors or incomplete runs are detected,
so the caller (runtests.sh) can detect failure via output capture.
Exits with code 1 on error, 0 on success.
"""

import fcntl
import glob
import os
import re
import sys


def main():
    branch = sys.argv[1] if len(sys.argv) > 1 else ""

    # Current directory name is the date-stamped run label
    run_dir = os.path.basename(os.getcwd())

    # index.html lives one level above the dated run directory
    index_file = os.path.join(os.path.dirname(os.getcwd()), "index.html")

    errors = []
    incomplete = []
    successes = []
    for html_path in sorted(glob.glob("*.html")):
        try:
            with open(html_path, 'r', errors='replace') as f:
                content = f.read()
        except OSError:
            continue
        for line in content.splitlines():
            if "Failure: Encountered" in line:
                errors.append((html_path, line.strip()))
                break
        if "</HTML>" not in content:
            incomplete.append(html_path)
        else:
            successes.append(html_path)

    # Remove files that had errors from successes
    error_fnames = {fname for fname, _ in errors}
    successes = [f for f in successes if f not in error_fnames]

    found_error = bool(errors or incomplete)
    if found_error:
        print("found an error!")

    label = f"{run_dir}<br>({branch})" if branch else run_dir
    new_row = f'<tr><td><a href="{run_dir}">{label}</a></td>\n'
    if found_error:
        new_row += '<td class="fail">'
        for fname, line in errors:
            new_row += f'<a href="{run_dir}/{fname}">{fname}: {line}</a><br>\n'
        for fname in incomplete:
            new_row += f'<a href="{run_dir}/{fname}">{fname}: INCOMPLETE</a><br>\n'
        new_row += '</td>\n'
    else:
        new_row += '<td class="ok"></td>\n'
    if successes:
        new_row += '<td class="ok">'
        for fname in successes:
            new_row += f'<a href="{run_dir}/{fname}">{fname}</a><br>\n'
        new_row += '</td>\n'
    else:
        new_row += '<td></td>\n'
    new_row += '</tr>\n'

    # Read header/footer from template (lives next to index.html).
    template_file = os.path.join(os.path.dirname(index_file), "index.template.html")
    try:
        with open(template_file, 'r') as tf:
            template = tf.read()
    except OSError:
        # Fallback: minimal embedded template if file is missing.
        template = (
            '<!DOCTYPE html>\n<html>\n<head><meta charset="utf-8">'
            '<title>TAU Regression Results</title>\n<style>\n'
            'body{background:#1a1a2e;color:#e0e0e0;font-family:monospace,sans-serif;padding:1rem}\n'
            'table{border-collapse:collapse;width:100%}\n'
            'tr{border-bottom:1px solid #333}\ntr:hover{background:#252540}\n'
            'td{padding:.4rem .9rem;vertical-align:top}\n'
            'td:first-child{white-space:nowrap;font-weight:bold;width:1%}\n'
            'td.fail{background:#3a1a1a;color:#e08080}\n'
            'td.ok{background:#1a3a1a;color:#7ec87e}\n'
            'a{color:inherit;text-decoration:none}\na:hover{text-decoration:underline}\n'
            '</style>\n</head>\n<body>\n<table>\n<!-- ROWS -->\n</table>\n</body>\n</html>\n'
        )

    marker = "<!-- ROWS -->"
    if marker in template:
        t_before, t_after = template.split(marker, 1)
    else:
        t_before, t_after = template, ""

    # Open with 'a+' to create index.html if it doesn't exist yet.
    # Acquire an exclusive lock before read-modify-write to handle
    # concurrent runs completing at the same time.
    with open(index_file, 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        existing_content = f.read()
        # Extract only <tr>...</tr> blocks, discarding any accumulated
        # header/footer noise from previous buggy writes.
        existing_rows = re.findall(r'<tr\b.*?</tr>\s*', existing_content, re.DOTALL)
        f.seek(0)
        f.truncate()
        f.write(t_before)
        f.write(new_row)
        f.writelines(existing_rows)
        f.write(t_after)

    return 1 if found_error else 0


if __name__ == '__main__':
    sys.exit(main())
