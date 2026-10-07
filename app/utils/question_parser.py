from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class ParsedQuestion:
    prompt: str
    options: list[str]
    answer_index: int
    difficulty: str = 'medium'
    explanation: str = ''


def parse_txt(content: str, limit: int = 100) -> tuple[list[ParsedQuestion], list[str]]:
    blocks = re.split(r'\n\s*\n', content.replace('\r\n', '\n').strip()) if content.strip() else []
    questions: list[ParsedQuestion] = []
    errors: list[str] = []
    seen: set[str] = set()
    answer_re = re.compile(r'^ANSWER\s*:\s*([ABCD])$', re.I)
    diff_re = re.compile(r'^DIFFICULTY\s*:\s*(easy|medium|hard)$', re.I)
    expl_re = re.compile(r'^EXPLANATION\s*:\s*(.*)$', re.I)

    for idx, block in enumerate(blocks, start=1):
        if len(questions) >= limit:
            errors.append(f'{limit} tadan ko‘p savol: {idx}-blokdan boshlab import qilinmadi.')
            break
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        prompt = re.sub(r'^\d+[.)]\s*', '', lines[0]).strip()
        options: list[str | None] = [None, None, None, None]
        answer_index: int | None = None
        difficulty = 'medium'
        explanation = ''
        for line in lines[1:]:
            match = re.match(r'^([ABCD])[).:]\s*(.+)$', line, re.I)
            if match:
                options[ord(match.group(1).upper()) - 65] = match.group(2).strip()
                continue
            match = answer_re.match(line)
            if match:
                answer_index = ord(match.group(1).upper()) - 65
                continue
            match = diff_re.match(line)
            if match:
                difficulty = match.group(1).lower()
                continue
            match = expl_re.match(line)
            if match:
                explanation = match.group(1).strip()

        problems = []
        if not prompt:
            problems.append('savol matni yo‘q')
        if any(option is None or not option for option in options):
            problems.append('A-D variantlar to‘liq emas')
        if answer_index is None:
            problems.append('ANSWER topilmadi')
        if problems:
            errors.append(f'{idx}-savol: ' + '; '.join(problems))
            continue
        key = re.sub(r'\s+', ' ', prompt.casefold())
        if key in seen:
            errors.append(f'{idx}-savol: duplicate savol')
            continue
        seen.add(key)
        questions.append(ParsedQuestion(prompt=prompt, options=[str(x) for x in options], answer_index=int(answer_index), difficulty=difficulty, explanation=explanation))
    return questions, errors
