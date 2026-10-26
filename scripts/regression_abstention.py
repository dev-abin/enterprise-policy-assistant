"""Post-evaluation regression only; not a new held-out score."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from policy_qa.service import Run
from policy_qa.llm import Ollama
from policy_qa.retrieval import PolicyIndex

run = Run(Ollama(), PolicyIndex(), prefix='regression', actor='automated_regression')
run.start('What is the daily meal allowance amount for international travel?')
assert run.state['final']['status'] == 'abstained'
assert 'No search' not in run.state['final']['answer']
record = {'type': 'post-evaluation regression, not held-out', 'final': run.state['final'],
          'trace': str(run.trace.path.relative_to(ROOT)), 'passed': True}
(ROOT / 'results/post_evaluation_regression.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record))
