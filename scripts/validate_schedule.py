"""Local development validator. This is NOT the organisers' validator.py."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.constraints import validate

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('dataset');parser.add_argument('schedule');args=parser.parse_args()
    report=validate(json.loads(Path(args.dataset).read_text()),json.loads(Path(args.schedule).read_text()))
    print(json.dumps(report,indent=2));sys.exit(0 if report['valid'] else 1)
