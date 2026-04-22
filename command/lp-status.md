# /lp-status

查看 LiteraturePipeline 状态。

## 检查 exports 记录数

```bash
python -c "import json; from pathlib import Path; data = json.loads(Path('99_System/PaperForge/exports/骨科.json').read_text('utf-8')); items = [i for i in data.get('items',[]) if i.get('itemType') != 'attachment']; print(f'骨科: {len(items)} records')"
```

## 检查 library-records 总数

```bash
python -c "from pathlib import Path; count = sum(1 for _ in Path('03_Resources/LiteratureControl/library-records').rglob('*.md')); print(f'library-records: {count} records')"
```

## 检查 OCR 完成数

```bash
python -c "from pathlib import Path; done = sum(1 for p in Path('99_System/PaperForge/ocr').glob('*/meta.json') if 'done' in Path(p).read_text('utf-8')); print(f'OCR done: {done}')"
```

## 检查索引记录数

```bash
python -c "import json; data = json.load(open('99_System/PaperForge/indexes/formal-library.json', encoding='utf-8')); print(f'Index: {len(data)} records')"
```