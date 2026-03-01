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
    -1, --once             Mine a single challenge then exit
    -s, --status           Print RPC status and exit
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

# Use a Solana wallet pubkey as miner identity
./pot-o-mine --pubkey 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU

# Check validator status
./pot-o-mine --status

# Crank up iterations for higher difficulty
./pot-o-mine --iterations 100000 --dim 512
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POT_RPC_URL` | RPC endpoint URL | `https://pot.rpc.gateway.tribewarez.com` |
| `POT_MINER_PUBKEY` | Miner identity string | `hostname-user-timestamp` |
| `POT_MAX_ITERATIONS` | Max nonce iterations | `10000` |
| `POT_MAX_TENSOR_DIM` | Max tensor dimension | `256` |
| `POT_LOOP_DELAY` | Seconds between cycles | `2` |
| `POT_VERBOSE` | Verbose output (1/0) | `0` |

## How It Works

1. **Fetch challenge** – `POST /challenge` returns a tensor challenge derived from the latest Solana slot hash, including the operation type, input tensor, difficulty, MML threshold, and neural path distance tolerance.

2. **Execute tensor operation** – The miner runs the specified operation (matrix multiply, convolution, ReLU, sigmoid, tanh, dot product, or normalize) on the input tensor.

3. **MML validation** – Computes the Minimum Message Length score: `compressed(output) / compressed(input)`. The score must be ≤ the challenge's MML threshold.

4. **Neural path search** – Iterates nonces, mixing each into the tensor output and running a feedforward pass through layers [32, 16, 8]. The binary activation pattern must match the expected path (derived from the challenge hash) within a Hamming distance tolerance.

5. **Submit proof** – `POST /submit` sends the proof (challenge ID, tensor hash, MML score, path signature, nonce, computation hash, miner pubkey) to the validator for on-chain submission.

## Architecture

```
pot-o-mine        # Single-file bash CLI with embedded Python mining engine
```

The mining computation (tensor ops, compression, neural path, SHA-256 hashing) runs in an embedded Python script using only standard library modules (`hashlib`, `zlib`, `struct`, `math`). The bash wrapper handles the RPC communication, argument parsing, display, and mining loop.

## License

Part of the Tribewarez testnet RPC infrastructure.
