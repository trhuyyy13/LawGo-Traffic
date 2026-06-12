"""Run evaluation against golden question set."""
import argparse

from lawgo_traffic.eval.evaluator import run_evaluation

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", default="data/eval/golden_questions.sample.json")
    args = parser.parse_args()
    run_evaluation(args.questions)
