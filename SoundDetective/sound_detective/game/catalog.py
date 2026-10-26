"""Registered case identities shared by loaders, saves and review validation."""
TIMBRE_IDS=tuple(f'T{i:02}' for i in range(1,10))
SOURCE_IDS=('W03','W04','W05','W06','W09')
MELODY_IDS=('W02','W07','W08')
WORDLE_IDS=tuple(f'W{i:02}' for i in range(1,10))
CASE_IDS=(*TIMBRE_IDS,*WORDLE_IDS,'M01')
