import pandas as pd

# Dateien einlesen
df_bench = pd.read_csv('./data/GlucoBench_benchmark_dataset.csv')
df_aligned1 = pd.read_csv('./data/HUPA0002P_aligned.csv')
df_aligned2 = pd.read_csv('./data/HUPA0011P_aligned.csv')

# Untereinanderfügen
df_combined = pd.concat([df_bench, df_aligned1, df_aligned2], ignore_index=True)

# Als CGM.csv speichern
df_combined.to_csv('./data/CGM.csv', index=False)