# pot-o-mine – PoT-O Desktop Miner CLI

A self-contained bash CLI that mines PoT-O (Proof of Tensor Optimizations) challenges on local PC hardware. Connects to the Tribewarez PoT-O RPC validator, fetches tensor challenges, performs all mining computation locally (tensor ops, MML compression, neural path matching), and submits proofs for on-chain verification and rewards.

## Requirements

- **bash** 4+
- **curl** (HTTP client)
- **jq** (JSON processing)
- **python3** (standard library only – no pip packages needed)

All dependencies are typically pre-installed on Linux and macOS. On Debian/Ubuntu:

```bash
sudo apt install curl jq python3
```

**Optional – Solana CLI** (for miner keypair identity, e.g. `solana-keygen new -o miner.json` and `-k $(solana-keygen pubkey miner.json)`). On Linux Mint 22.3 / Debian / Ubuntu:

```bash
./install-solana-cli.sh
# or pin version: SOLANA_INSTALL_VERSION=v3.1.9 ./install-solana-cli.sh
```

If `solana airdrop` (or other commands) report **"No default signer found"** after creating a keypair, set the keypair path explicitly:

```bash
solana config set --keypair ~/.config/solana/id.json
# or for a project keypair:
solana config set --keypair ~/pot-o-miner-cli/mineri.json
solana config set --url https://testnet-solana.rpc.gateway.tribewarez.com
solana airdrop 10
```

## Quick Start

```bash
# Clone and run
git clone <this-repo-url> pot-o-miner-cli
cd pot-o-miner-cli
chmod +x pot-o-mine
./pot-o-mine
```

## Usage

```
pot-o-mine [OPTIONS]

OPTIONS:
    -r, --rpc URL          RPC endpoint (default: https://pot.rpc.gateway.tribewarez.com)
    -k, --pubkey KEY       Miner public key / identity
    -i, --iterations N     Max nonce iterations per challenge (default: 10000)
    -d, --dim N            Max tensor dimension (default: 256)
    -D, --delay SECS       Delay between mining cycles (default: 2)
    -o, --op TYPE          Prefer tensor op (matrix_multiply, convolution, relu, sigmoid, tanh, dot_product, normalize)
    --path-layers W,W,W    Neural path layer widths (default: 32,16,8)
    --mml-threshold R      Override MML threshold
    --explain              Print step-by-step MML/path calculation to stderr
    -1, --once             Mine a single challenge then exit
    -s, --status           Print RPC status and exit
    --dashboard            Run live stats dashboard (TUI)
    --pool                 Print pool info and exit
    --peers                Print network peers and exit
    --devices              Print registered devices (GET /devices) and exit
    --miner-info KEY       Print miner account for pubkey and exit
    --register-device JSON Register an ESP/external device (JSON body)
    --service-status ID    Status API: single service (solana-rpc-proxy, pot-o-validator, etc.)
    -v, --verbose          Verbose output
    -h, --help             Show help
```

## Examples

```bash
# Mine continuously on the public testnet
./pot-o-mine

# Mine against a local validator
./pot-o-mine --rpc http://localhost:8900

# Mine a single challenge and exit
./pot-o-mine --once --verbose

# Use a Solana wallet pubkey or keypair file as miner identity
./pot-o-mine --pubkey Cycv3ov14zd2dXMUfS2JPMz9r4bpQAPLfQDKxis2tjCg
./pot-o-mine -k $(solana-keygen pubkey miner.json)   # identity from miner.json keypair (use your keypair filename, e.g. mineri.json)

# Check validator status
./pot-o-mine --status

# Live dashboard (health, status, pool, peers, miner info)
./pot-o-mine --dashboard

# Pool info, network peers, registered devices
./pot-o-mine --pool
./pot-o-mine --peers
./pot-o-mine --devices

# Miner account (on-chain proxy)
./pot-o-mine --miner-info 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU

# Status API: single service (eth-rpc, solana-rpc, solana-rpc-proxy, pot-o-validator)
./pot-o-mine --service-status solana-rpc-proxy

# Crank up iterations for higher difficulty
./pot-o-mine --iterations 100000 --dim 512

# Prefer tensor op, custom path layers, and show calculation steps
./pot-o-mine --once --op matrix_multiply --path-layers 32,16,8 --explain
./pot-o-mine --mml-threshold 0.5 --explain
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POT_RPC_URL` | RPC endpoint URL | `https://pot.rpc.gateway.tribewarez.com` |
| `POT_MINER_PUBKEY` | Miner identity string | `hostname-user-timestamp` |
| `POT_MAX_ITERATIONS` | Max nonce iterations | `10000` |
| `POT_MAX_TENSOR_DIM` | Max tensor dimension | `256` |
| `POT_LOOP_DELAY` | Seconds between cycles | `2` |
| `POT_OPERATION` | Prefer tensor op (same as `--op`) | (challenge default) |
| `POT_PATH_LAYERS` | Comma-sep path layer widths (e.g. `32,16,8`) | `32,16,8` |
| `POT_MML_THRESHOLD` | Override MML threshold | (challenge default) |
| `POT_EXPLAIN` | `1` = print calculation steps to stderr | `0` |
| `POT_STATUS_URL` | Status API base (dashboard, --service-status) | `https://status.rpc.gateway.tribewarez.com` |
| `POT_MINER_JSON` | Path to JSON file with submit signature (array of ints) | (none; else `miner.json` in script dir or CWD) |
| `POT_SUBMIT_SIGNATURE` | Submit signature as JSON array (overrides file) | (none) |
| `POT_VERBOSE` | Verbose output (1/0) | `0` |

## How It Works

1. **Fetch challenge** – `POST /challenge` returns a tensor challenge derived from the latest Solana slot hash, including the operation type, input tensor, difficulty, MML threshold, and neural path distance tolerance.

2. **Execute tensor operation** – The miner runs the specified operation (matrix multiply, convolution, ReLU, sigmoid, tanh, dot product, or normalize) on the input tensor.

3. **MML validation** – Computes the Minimum Message Length score: `compressed(output) / compressed(input)`. The score must be ≤ the challenge's MML threshold.

4. **Neural path search** – Iterates nonces, mixing each into the tensor output and running a feedforward pass through layers [32, 16, 8] (configurable via `--path-layers`). The binary activation pattern must match the expected path (derived from the challenge hash) within a Hamming distance tolerance.

5. **Submit proof** – `POST /submit` sends the proof (challenge ID, tensor hash, MML score, path signature, nonce, computation hash, miner pubkey) to the validator for on-chain submission.

---

## How the calculation is done

Use **`--explain`** (or `POT_EXPLAIN=1`) to print step-by-step calculation to stderr.

### Tensors used

- **Input tensor** — From the challenge: `input_tensor.shape.dims` (e.g. `[64, 64]`) and `input_tensor.data.F32` (float32 list). If the challenge provides fewer elements than `rows × cols`, the rest are filled with a deterministic seed.
- **Output tensor** — Result of applying the chosen **tensor op** to the input. Shape depends on the op (e.g. matrix_multiply keeps shape; convolution yields a 1D vector; dot_product yields a single scalar).

### Tensor operations (choose with `-o` / `--op`)

| Op | Description | Output shape |
|----|-------------|--------------|
| `matrix_multiply` | A × A (same matrix squared) | rows×cols |
| `convolution` | 1D kernel [0.25, 0.5, 0.25] over data | 1×(n−2) |
| `relu` | max(0, x) per element | same as input |
| `sigmoid` | 1/(1+e^{-x}) | same as input |
| `tanh` | tanh(x) | same as input |
| `dot_product` | dot(first half, second half) | 1×1 |
| `normalize` | x / ‖x‖ | same as input |

The challenge’s `operation_type` is used unless you override with **`--op`**.

### MML score (which MML is used / improved)

- **Formula:** `MML = len(zlib.compress(output_bytes, 6)) / len(zlib.compress(input_bytes, 6))`.
- **Interpretation:** Ratio of compressed output size to compressed input size. **Lower is better.** A valid proof must have `MML ≤ mml_threshold` from the challenge (or **`--mml-threshold`** if set).
- **To “improve” MML:** You need an output that compresses better relative to the input (e.g. more regular structure). The miner does not optimize MML directly; it runs the fixed op and then checks the score. Tighter threshold = harder challenges.

### Path calculation

- **Layer widths** — Configurable with **`--path-layers`** (e.g. `32,16,8`). Each layer reduces the current activation vector to `width` values; each value is turned into 1 bit (1 if sum > 0, else 0).
- **Expected path** — Derived from the challenge ID: SHA256(challenge_id) is used to seed a deterministic bit sequence over the layers (one bit per neuron per layer).
- **Actual path** — From the **output tensor**: add a nonce-dependent perturbation (`sin(nonce + i) * 0.1`), then run the same layer reduction and thresholding. This gives a bit string.
- **Match** — Hamming distance between actual and expected path must be **≤ path_distance_max** (from the challenge). The miner searches nonces until it finds one that meets this bound, then builds the proof (path_signature hex, computation_hash, etc.).

## API Reference (RPC base: `https://pot.rpc.gateway.tribewarez.com`)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Liveness check (service, version) |
| `GET /status` | Mining stats, difficulty, engine, network peers |
| `POST /challenge` | Get mining challenge (body: `slot`, `slot_hash`, `device_type`) |
| `POST /submit` | Submit proof (body: `proof`, `signature`) |
| `GET /miners/:pubkey` | Miner account (proxied from on-chain) |
| `GET /pool` | Pool info (type, miners, stake, minimum_stake) |
| `GET /network/peers` | List known peers |
| `GET /devices` | Registered devices (device_count, list) |
| `POST /devices/register` | Register ESP or external mining device |

Optional env for challenge: `POT_SLOT`, `POT_SLOT_HASH`. For submit signature: `POT_SUBMIT_SIGNATURE` (JSON array) or `miner.json` (see Key auth below).

---

## API integration summary

| Method | Endpoint | Body / params | CLI / dashboard |
|--------|----------|----------------|------------------|
| GET | `/health` | — | Used at startup |
| GET | `/status` | — | `--status`, dashboard (PoT-O live) |
| POST | `/challenge` | `{ "slot?", "slot_hash?", "device_type" }` | Mining loop |
| POST | `/submit` | `{ "proof", "signature" }` | After proof found |
| GET | `/miners/:pubkey` | — | `--miner-info KEY`, dashboard |
| GET | `/pool` | — | `--pool`, dashboard |
| GET | `/network/peers` | — | `--peers`, dashboard |
| GET | `/devices` | — | `--devices`, dashboard |
| POST | `/devices/register` | JSON body | `--register-device '{}'` |

**Status API** (base: `POT_STATUS_URL`, default `https://status.rpc.gateway.tribewarez.com`):

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/status` | All services status (summary + per-service); dashboard |
| GET | `/status/:id` | Single service: `eth-rpc`, `solana-rpc`, `solana-rpc-proxy`, `pot-o-validator` |
| GET | `/service/:id` | Same as `/status/:id`; `--service-status` |
| GET | `/openapi.json` | OpenAPI 3.0 spec |
| GET | `/api/live` | Full live: services + PoT-O state (+ ai_backend, swap_snapshot); dashboard |
| GET | `/api/live/stream` | SSE stream (same payload every 2s) |
| GET | `/api/blocks` | Recent challenge/block history |
| GET | `/api/miners` | Miners by device (ESP32, ESP8266, GPU, CPU, native, WASM); dashboard |
| GET | `/api/ai-backend` | AI backend status (env-driven, sanitized) |
| GET | `/api/swap-snapshot` | Token swap snapshot (NMTC, PTTC, SOL) |
| GET | `/api/swap-quote` | Swap quote: `?from_token=NMTC&to_token=PTTC&amount_in=...` |
| GET | `/docs` | Swagger UI |

**Monitored services:** eth-rpc, solana-rpc, solana-rpc-proxy, pot-o-validator. The root `/` serves the Explorer dashboard (services, PoT-O section, swap quote, block timeline, etc.). Live refresh every 5s or via `/api/live/stream`.

---

## Key auth

- **Miner identity (pubkey)**  
  - Set via `-k` / `--pubkey` or `POT_MINER_PUBKEY`.  
  - Included in every proof as `miner_pubkey` (on-chain identity; can be a Solana wallet pubkey or any string).  
  - No HTTP auth headers: the validator does not use `Authorization`; identity is in the proof payload.

- **Submit signature**  
  - `POST /submit` body: `{ "proof": {...}, "signature": [ ... ] }`.  
  - `signature` is an optional array of bytes (e.g. 64 integers for an Ed25519 signature).  
  - **Source (in order):**  
    1. Env **`POT_SUBMIT_SIGNATURE`** – JSON array (e.g. a real proof signature).  
    2. File **`POT_MINER_JSON`** – path to a JSON file that is the **signature** array (not a keypair).  
    3. **`miner.json`** – only if it is **not** a Solana keypair (see below).  
  - If the file is a 64-integer array, the CLI treats it as a keypair and **never** sends it as `signature` (that would expose the private key).  
  - If none are set, `signature` is sent as `[]`.

- **`miner.json` from `solana-keygen new -o miner.json`**  
  - This file is a **Solana keypair** (64-byte secret). Use it **only for identity**, not as signature:  
    `./pot-o-mine -k $(solana-keygen pubkey miner.json)`  
  - The CLI will **not** send its contents as `signature` (it detects 64-byte arrays and skips them to avoid leaking the key).  
  - To sign proofs you must produce the Ed25519 signature elsewhere and pass it via **`POT_SUBMIT_SIGNATURE`**, or use a validator that does not require a signature.

---

## Architecture

```
pot-o-mine              # Bash CLI with embedded Python mining engine
pot-o-mine-dashboard.py # TUI dashboard (--dashboard)
```

The mining computation (tensor ops, compression, neural path, SHA-256 hashing) runs in an embedded Python script using only standard library modules (`hashlib`, `zlib`, `struct`, `math`). The bash wrapper handles the RPC communication, argument parsing, display, and mining loop.

## License

Part of the Tribewarez testnet RPC infrastructure.
