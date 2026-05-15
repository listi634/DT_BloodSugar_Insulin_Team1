import pandas as pd
import os

def align_to_benchmark(input_csv, reference_csv, output_csv):
    # Daten laden
    df = pd.read_csv(input_csv, sep=';')
    # Spaltennamen des Benchmark-Datensatzes extrahieren
    ref_cols = pd.read_csv(reference_csv, nrows=0).columns.tolist()
    
    # Mapping der vorhandenen Spalten
    mapping = {
        'time': 'timestamp',
        'carb_input': 'carbs',
        'steps': 'exercise_steps',
        'basal_rate': 'insulin_basal',
        'bolus_volume_delivered': 'insulin_bolus'
    }
    
    # Spalten umbenennen
    df = df.rename(columns=mapping)
    
    # user_id aus Dateiname (ohne Endung)
    df['user_id'] = os.path.splitext(os.path.basename(input_csv))[0]
    
    # Fehlende Benchmark-Spalten mit 0 ergänzen
    for col in ref_cols:
        if col not in df.columns:
            df[col] = 0
            
    # Nur relevante Spalten in der richtigen Reihenfolge behalten
    df_aligned = df[ref_cols]
    
    df_aligned['timestamp'] = pd.to_datetime(df_aligned['timestamp'], errors='coerce')
    
    # Speichern
    df_aligned.to_csv(output_csv, index=False)
    return df_aligned

# Ausführung
align_to_benchmark('./data/HUPA0002P.csv', './data/GlucoBench_benchmark_dataset.csv', './data/HUPA0002P_aligned.csv')