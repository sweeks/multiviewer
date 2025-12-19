#!/usr/bin/env python
from multiviewer.mv_screen import MvScreen


def main():
    mv = MvScreen()
    states, transitions, complete = mv.explore_fsm(
        max_states=10_000_000, report_powers_of_two=True
    )
    print(f"done: states={states} transitions={transitions} complete={complete}")


if __name__ == "__main__":
    main()
