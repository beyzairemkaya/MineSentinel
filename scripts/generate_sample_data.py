import pandas as pd
import numpy as np
import os

def generate_sample_data(num_samples=100):
    np.random.seed(42)
    # there are 4 possible sitiutaion that we need to create 
    
    # number of samples seperate according to different sitiutaion
    n_normal=int(num_samples*0.7)
    n_gas=int(num_samples*0.15)
    n_fall=int(num_samples*0.10)
    n_critical = num_samples - (n_normal + n_gas + n_fall)

    # Scenerio 1 Normal
    gas_normal=np.random.normal(loc=150,scale=20,size=n_normal)
    acc_normal=np.random.normal(loc=1,scale=0.03,size=n_normal)
    duration_normal=np.zeros(n_normal,dtype=int)
    labels_normal=["normal"]*n_normal

    # Scenerio 2 Gas Warning
    gas_gas=np.random.uniform(low=400,high=950,size=n_gas)
    acc_gas=np.random.normal(loc=1,scale=0.03,size=n_gas)
    duration_gas=np.random.randint(1,9,size=n_gas)
    labels_gas=["warning_gas"]*n_gas

    # Scenerio 3 Acceleration Warning 
    gas_acc=np.random.normal(loc=150,scale=20,size=n_fall)
    acc_acc=np.random.uniform(low=2.5,high=4.8,size=n_fall)
    duration_acc=np.random.randint(1,6,size=n_fall)
    labels_acc=["warning_fall"]*n_fall

    #Scenerio 4 Falling
    gas_critical=np.random.uniform(low=600,high=1000,size=n_critical)
    acc_critical=np.random.uniform(low=3,high=5,size=n_critical)
    duration_critical=np.random.randint(4,12,size=n_critical)
    labels_critical=["critical"]*n_critical

    gas=np.concatenate([gas_normal,gas_gas,gas_acc,gas_critical])
    accel=np.concatenate([acc_normal,acc_gas,acc_acc,acc_critical])
    duration=np.concatenate([duration_normal,duration_gas,duration_acc,duration_critical])
    labels=np.concatenate([labels_normal,labels_gas,labels_acc,labels_critical])

    df = pd.DataFrame({
        "gas_ppm": np.round(gas, 2),
        "accel_g": np.round(accel, 2),
        "duration_sec": duration,
        "label": labels
    })

    # 5. Satırları Rastgele Karıştır (Shuffle)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    return df

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    df_data = generate_sample_data(num_samples=1000)
    output_path = os.path.join(data_dir, "sample_sensor_data.csv")
    df_data.to_csv(output_path, index=False)

    print(f"Veri seti başarıyla kaydedildi: {output_path}")
    


