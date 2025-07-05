import numpy as np
import talib
from sklearn.neighbors import NearestNeighbors


def lorentzian_distance(X, Y):
    """
    Calcula la distancia de Lorentz entre dos arrays de features.
    X, Y: arrays de shape (n_features,)
    """
    return np.sum(np.log(1 + np.abs(X - Y)))

def compute_features(close, high, low, features_config):
    """
    Calcula las features seleccionadas para los arrays de OHLCV.

    features_config: lista de tuplas (nombre, paramA, paramB)
        - nombre: nombre del indicador (str)
        - paramA: parámetro principal (int, por ejemplo, periodos)
        - paramB: parámetro secundario (int, opcional, depende del indicador)
    Ejemplo:
        features_config = [
            ('RSI', 14, 0),
            ('CCI', 20, 0),
            ('STOCH', 14, 3)  # Ejemplo: STOCH usa dos parámetros
        ]
    Devuelve un array shape (n_samples, n_features)
    """
    feats = []
    for name, a, b in features_config:
        if name == 'RSI':
            feats.append(talib.RSI(close, timeperiod=a))
        elif name == 'CCI':
            feats.append(talib.CCI(high, low, close, timeperiod=a))
        elif name == 'ADX':
            feats.append(talib.ADX(high, low, close, timeperiod=a))
        elif name == 'WT':
            # Williams %R como aproximación a WaveTrend
            feats.append(talib.WILLR(high, low, close, timeperiod=a))
        elif name == 'STOCH':
            # Ejemplo de uso de dos parámetros: STOCH (paramA=fastk_period, paramB=slowk_period)
            stoch_k, stoch_d = talib.STOCH(high, low, close, fastk_period=a, slowk_period=b)
            feats.append(stoch_k)
        else:
            feats.append(close)
    return np.column_stack(feats)

class LorentzianNearestNeighbors(NearestNeighbors):
    def __init__(self, n_neighbors=8):
        super().__init__(n_neighbors=n_neighbors, metric='precomputed')
        
    def _compute_lorentzian_distances(self, X, Y=None):
        if Y is None:
            Y = X
        n_samples_X = X.shape[0]
        n_samples_Y = Y.shape[0]
        distances = np.zeros((n_samples_X, n_samples_Y))
        
        for i in range(n_samples_X):
            for j in range(n_samples_Y):
                distances[i, j] = lorentzian_distance(X[i], Y[j])
        return distances
    
    def fit(self, X, y=None):
        self.X_ = X
        self.y_ = y
        return self
    
    def kneighbors(self, X=None, n_neighbors=None, return_distance=True):
        if X is None:
            X = self.X_
        if n_neighbors is None:
            n_neighbors = self.n_neighbors
            
        distances = self._compute_lorentzian_distances(X, self.X_)
        indices = np.argsort(distances, axis=1)[:, :n_neighbors]
        
        if return_distance:
            distances = np.take_along_axis(distances, indices, axis=1)
            return distances, indices
        return indices

def lorentzian_knn_predict(X, y, x_query, n_neighbors=8):
    """
    Predicción KNN usando distancia de Lorentz con implementación scikit-learn.
    X: matriz de features de entrenamiento
    y: etiquetas
    x_query: vector de features a predecir
    """
    knn = LorentzianNearestNeighbors(n_neighbors=n_neighbors)
    knn.fit(X, y)
    distances, indices = knn.kneighbors(x_query.reshape(1, -1))
    votes = y[indices[0]]
    vals, counts = np.unique(votes, return_counts=True)
    return vals[np.argmax(counts)] 