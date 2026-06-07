txt = open(r"D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_document.py", encoding="utf-8").read()
idx = txt.find('last_insert_anchor_kind == "box"')
if idx >= 0:
    print(txt[idx:idx+700])
else:
    print("NOT FOUND")
