import re, sys

paths = [
    r"D:\Tools\deepseek-tui\node_modules\deepseek-tui\bin\downloads\deepseek-tui.exe",
    r"D:\Tools\deepseek-tui\node_modules\deepseek-tui\bin\downloads\deepseek.exe",
]

url_re = re.compile(rb"https?://[A-Za-z0-9\.\-_/:%\?=&~+]+")
key_re = re.compile(rb"sk-[A-Za-z0-9]{20,}")

for p in paths:
    print("=" * 20, p)
    try:
        data = open(p, "rb").read()
    except OSError as e:
        print("ERR", e)
        continue
    ascii_urls = sorted(set(url_re.findall(data)))
    print("ASCII URLs:", len(ascii_urls))
    for u in ascii_urls[:50]:
        print("  ", u.decode("latin1"))
    keys = sorted(set(key_re.findall(data)))
    print("API keys found:", len(keys))
    for k in keys[:5]:
        print("  ", k.decode("latin1"))
    # UTF-16LE scan for urls
    try:
        text16 = data.decode("utf-16-le", "ignore")
        raw16 = text16.encode("latin1", "ignore")
        urls16 = sorted(set(url_re.findall(raw16)))
        print("UTF16 URLs:", len(urls16))
        for u in urls16[:50]:
            print("  ", u.decode("latin1"))
    except Exception as e:
        print("utf16 err", e)
