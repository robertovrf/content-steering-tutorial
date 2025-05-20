import threading

from collections import deque
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from monitor import monitor


class AIServerSelector:
    def __init__(self, max_samples=1000, update_threshould=100):
        self.max_samples = max_samples

        self.data_buffer   = deque(maxlen=max_samples)
        self.target_buffer = deque(maxlen=max_samples)

        self.scaler            = StandardScaler()
        self.update_threshould = update_threshould
        self.model             = None
        self.sample_count      = 0
        self.server_mapping    = {}
        self.load_or_train_model()

        self.lock = threading.Lock()


    def load_or_train_model(self):
        try:
            self.model  = joblib.load('server_selection_model.joblib')
            self.scaler = joblib.load('server_selection_scaler.joblib')
            self.server_mapping = joblib.load('server_selection_mapping.joblib')

            print("Model loaded successfully.")

        except FileNotFoundError:
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            dummy_data = []
            dummy_targets = []

            # Generate dummy data for different combinations of features
            feature_combinations = [
                (latency, packet_loss, bandwidth, cpu_usage, memory_usage)
                    for latency in [50, 100, 200]
                    for packet_loss in [0.1, 0.5, 1]
                    for bandwidth in [5000, 10000, 20000]
                    for cpu_usage in [20, 50, 80]
                    for memory_usage in [30, 60, 90]
            ]

            for features in feature_combinations:
                qoe = self.calculate_qoe(*features)
                dummy_data.append(features)
                dummy_targets.append(qoe)

            # Prepare and scale the dummy data
            dummy_data = np.array(dummy_data)
            dummy_targets = np.array(dummy_targets)

            self.scaler.fit(dummy_data)
            scaled_data = self.scaler.transform(dummy_data)

            # Train the model with the scaled data
            self.model.fit(scaled_data, dummy_targets)
            self.server_mapping = {}

            # Save the trained model, scaler, and mapping
            joblib.dump(self.model, 'server_selection_model.joblib')
            joblib.dump(self.scaler, 'server_selection_scaler.joblib')
            joblib.dump(self.server_mapping, 'server_selection_mapping.joblib')

            print("Model not found. Training a new model.")


    def calculate_qoe(self, latency, packet_loss, bandwidth, cpu_usage, memory_usage):
        qoe = 5 - (latency / 100) \
              - (packet_loss / 2) \
              - (cpu_usage / 100) \
              - (memory_usage / 100)
        qoe += bandwidth / 100000
        
        return max(min(qoe, 5), 1)
    
    
    def predict_best_server(self, network_conditions, available_servers):
        if not available_servers:
            print("Nenhum servidor disponível para seleção.")
            return None
        
        server_metrics = self.get_server_metrics(available_servers)
        qoe_predictions = []

        for metrics in server_metrics:
            features = [
                network_conditions['latency'],
                network_conditions['packet_loss'],
                network_conditions['bandwidth'],
                metrics['cpu_usage'],
                metrics['memory_usage']
            ]

            input_data = np.array([features])

            try:
                input_data_scsaled = self.scaler.transform(input_data)
            except Exception as e:
                print(f"Erro ao escalar os dados de entrada: {e}")
                continue

            with self.lock:
                try:
                    qoe = self.model.predict(input_data_scsaled)[0]
                except Exception as e:
                    print(f"Erro ao prever QoE: {e}")
                    qoe = 0

            qoe_predictions.append((qoe, metrics['server_name']))

            if not qoe_predictions:
                print("Nenhum QoE previsto.")
                return None
            
        best_server = max(qoe_predictions, key=lambda x: x[0])[1]

        print(
            f"Servidor selecionado: {best_server} com "
            f"QoE: {max(qoe_predictions, key=lambda x: x[0])[0]}"
        )
        return best_server
    

    def get_server_metrics(self, available_servers):
        metrics = []
        for server in available_servers:
            server_name = server[0]
            try:
                cpu_usage    = monitor.get_cpu_usage(server_name)
                memory_usage = monitor.get_memory_usage(server_name)

            except AttributeError:
                print(
                    f"Não foi possível obter métricas para {server_name}. " 
                    f"Usando valores padrão."
                )
                cpu_usage = 0
                memory_usage = 0
            
            metrics.append({
                'server_name': server_name,
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage
            })
        return metrics


    def update_model(
        self, 
        network_conditions, 
        selected_server, 
        performance, 
        available_servers
    ):
        if not selected_server:
            print("Nenhum servidor selecionado para atualização do modelo.")
            return

        
        server_metrics = self.get_server_metrics(available_servers)
        selected_metrics = next(
            (metrics for metrics in server_metrics if metrics['server_name'] == selected_server), 
            None
        )
        if selected_metrics is None:
            print(f"Métricas do servidor {selected_server} não encontradas.")
            return

        features = [
            network_conditions['latency'],
            network_conditions['packet_loss'],
            network_conditions['bandwidth'],
            selected_metrics['cpu_usage'],
            selected_metrics['memory_usage']
        ]

        with self.lock:
            self.data_buffer.append(features)
            self.target_buffer.append(performance)
            self.sample_count += 1

            if self.sample_count >= self.update_threshold:
                self._perform_model_update()


    def _perform_model_update(self):
        X = np.array(self.data_buffer)
        y = np.array(self.target_buffer)

        if len(X) == 0:
            print(
                "Nenhum dado disponível para atualização do modelo."
            )
            return

        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)

        try:
            self.model.fit(X_scaled, y)
        except Exception as e:
            print(f"Erro ao treinar o modelo: {e}")
            return

        joblib.dump(self.model, 'server_selection_model.joblib')
        joblib.dump(self.scaler, 'server_selection_scaler.joblib')

        self.sample_count = 0
        print(f"Modelo atualizado com {len(X)} amostras.")


    def get_model_performance(self):
        with self.lock:
            return {
                "samples_collected": len(self.data_buffer),
                "updates_performed": self.sample_count // self.update_threshold
            }