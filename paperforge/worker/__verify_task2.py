"""Verify Task 2 acceptance criteria for pf-paper.md."""
from __future__ import annotations
import re
import sys

content = open('paperforge/skills/literature-qa/scripts/pf-paper.md', encoding='utf-8').read()
checks = [
    ('grep: 保存讨论记录', bool(re.search('保存讨论记录', content))),
    ('grep: paperforge.worker.discussion record', bool(re.search(r'paperforge\.worker\.discussion record', content))),
    ('grep: 仅.*pf-paper.*记录', bool(re.search('仅.*pf-paper.*记录', content))),
    ('grep: pf-deep.*不记录', bool(re.search('pf-deep.*不记录', content))),
    ('grep: ai/discussion.json >= 1', content.count('ai/discussion.json') >= 1),
    ('grep: ai/discussion.md >= 1', content.count('ai/discussion.md') >= 1),
    ('grep: user_question', 'user_question' in content),
    ('grep: agent_analysis', 'agent_analysis' in content),
    ('grep: ## See Also preserved', '## See Also' in content),
    ('grep: prerequisite discussion.py', 'discussion.py 模块可用' in content),
    ('grep: output recording mention', '会话结束后，讨论记录将自动保存' in content),
]
all_pass = True
for name, result in checks:
    status = 'PASS' if result else 'FAIL'
    if not result:
        all_pass = False
    print(f'[{status}] {name}')
print(f'\nAll checks: {"PASS" if all_pass else "FAIL"}')
sys.exit(0 if all_pass else 1)
