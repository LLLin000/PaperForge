# clarify-user-intent

Clarifies ambiguous user intent when SKILL.md cannot confidently route.

## Trigger conditions

- Input is too short or vague
- Input matches multiple top-level intents
- Required object (paper key/DOI/title) is missing
- User says "这篇" but no unique paper is locked in context

## Interaction rules

1. Explain briefly what PaperForge can do
2. Present options matching the 5 research intents + mechanical commands
3. Let user choose or provide more details
4. Maximum 2 rounds of clarification; after that, report inability to route

Two-round limit: 最多两轮。两轮后仍无法确定，告知用户无法路由。

## Fixed question pattern (Chinese)

```
我可以帮你做这几类事：

1. 找某篇文章
2. 找一批相关论文
3. 找支持某个观点/参数/术语的证据
4. 精读一篇文章
5. 记录到项目阅读笔记 / 保存

你现在更想做哪一种？如果你已经有 paper key / DOI / 标题，也可以直接发给我。
```

## Output

Returns one: `clarified_intent` matched to the compound's top-level intents.

## Two-round limit rule

最多两轮。两轮后仍无法确定，告知用户无法路由。
