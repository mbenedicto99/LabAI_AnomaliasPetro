import numpy as np, torch, torch.nn as nn, torch.optim as optim
from scipy.signal import welch

# --- simulador (sdof) ---
def simulate_sdof(T=1800, fs=200, m=1.0, c=0.02, k=1000.0, damage_t=900, delta=0.02):
    n = T*fs; dt = 1/fs
    x = np.zeros(n); v = np.zeros(n); a = np.zeros(n)
    k_t = k
    forcing = 0.1*np.random.randn(n)
    strain = np.zeros(n)
    for i in range(1,n):
        if i==damage_t*fs: k_t = k*(1-delta)
        a[i] = (forcing[i] - c*v[i-1] - k_t*x[i-1]) / m
        v[i] = v[i-1] + a[i]*dt
        x[i] = x[i-1] + v[i]*dt
        strain[i] = x[i] * k_t  # proxy simples
    accel = a + 0.02*np.random.randn(n)
    temp = 20 + 5*np.sin(np.linspace(0,10,n)) + 0.2*np.random.randn(n)
    return accel, strain, temp, fs

# --- features ---
def features(accel_win, strain_win, temp_win, fs):
    f, Pxx = welch(accel_win, fs=fs, nperseg=min(len(accel_win)//2, 512))
    f1 = f[np.argmax(Pxx[(f>0.1)&(f<50)])]  # pico bruto (ajuste fino depois)
    rms = np.sqrt(np.mean(accel_win**2))
    st_mean = np.mean(strain_win); st_slope = np.polyfit(np.arange(len(strain_win)), strain_win, 1)[0]
    t_mean = np.mean(temp_win)
    return np.array([f1, rms, st_mean, st_slope, t_mean], dtype=np.float32)

# --- modelos SGD ---
class AE(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(d,16), nn.ReLU(), nn.Linear(16,8))
        self.dec = nn.Sequential(nn.Linear(8,16), nn.ReLU(), nn.Linear(16,d))
    def forward(self,x): z = self.enc(x); return self.dec(z)

# loop online
accel, strain, temp, fs = simulate_sdof()
win = 800     # 4 s @200 Hz
step = 400    # 50% overlap
X_hist, scores, f1_obs = [], [], []
# baseline linear para f1: y = w^T u (u = [rms, st_mean, st_slope, t_mean, 1])
w = torch.zeros(5, requires_grad=True)
opt_lin = optim.SGD([w], lr=1e-3)
ae = AE(d=4); opt_ae = optim.SGD(ae.parameters(), lr=1e-3)
ma_scores = []

for start in range(0, len(accel)-win, step):
    sl = slice(start, start+win)
    accw, stw, tw = accel[sl], strain[sl], temp[sl]
    feats = features(accw, stw, tw, fs)
    f1, u = feats[0], torch.tensor(np.r_[feats[1:4], feats[4:5], 1.0]).float()  # 4 inputs + bias
    # --- baseline linear (pred f1) ---
    yhat = (w*u).sum()
    loss_lin = (yhat - torch.tensor(f1).float())**2
    opt_lin.zero_grad(); loss_lin.backward(); opt_lin.step()
    # --- autoencoder no vetor [rms, st_mean, st_slope, t_mean] ---
    xin = torch.tensor(feats[1:5]).float().unsqueeze(0)
    xrec = ae(xin); loss_ae = ((xrec - xin)**2).mean()
    opt_ae.zero_grad(); loss_ae.backward(); opt_ae.step()
    # --- score e thr adaptativo ---
    score = float(abs(f1 - float(yhat.detach()))) + float(loss_ae.detach())
    ma_scores.append(score); window_thr = np.quantile(ma_scores[-120:], 0.99) if len(ma_scores)>120 else np.inf
    alert = score > window_thr
    scores.append((score, window_thr, alert))
    f1_obs.append(f1)
