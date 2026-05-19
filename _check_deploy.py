import sys
sys.stdout.reconfigure(encoding="utf-8")
path = r"D:\L\OB\Literature-hub\.obsidian\plugins\paperforge\main.js"
s = open(path, "r", encoding="utf-8").read()
print("No PDF in file:", "No PDF" in s)
print("t(orphan_explain) in file:", "orphan_explain" in s)
print("Hardcoded 'Delete ' in orphan section:", s[s.find("orphan-modal-actions")-200:s.find("orphan-modal-actions")+500] if "orphan-modal-actions" in s else "NOT FOUND")
