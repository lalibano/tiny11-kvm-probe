# Tiny11 KVM image builder

This is the public, no-secrets GitHub Actions builder for the Tiny11 Kaggle plan.

## Why this repository is public

GitHub's public `ubuntu-latest` runner exposed `/dev/kvm` in the probe. The private repository's runner did not. This repository contains only build scripts and a workflow; it contains no VM image, Kaggle token, Tailscale key, or other credential.

## Workflow

Run **Actions → Build preinstalled Tiny11 image → Run workflow**.

- `probe` verifies KVM without using secrets.
- `build` downloads the private ISO from Kaggle, performs unattended UEFI/GPT installation with QEMU/KVM, and waits for a real RDP handshake. The UEFI path is required because the Tiny11 25H2 ISO does not expose a usable SeaBIOS boot path on the hosted runner.
- `publish_dataset=true` uploads the resulting qcow2 to the configured private Kaggle dataset.

The build mode requires one of these GitHub Actions secret configurations:

- `KAGGLE_API_TOKEN`, or
- `KAGGLE_USERNAME` and `KAGGLE_KEY`.

`TINY11_BUILD_PASSWORD` is optional; if omitted, the workflow generates a temporary bootstrap password. The unattended setup clears it after first logon and enables the `RDP` account for the later Kaggle runtime.

The Tailscale auth key is deliberately not used by this public build workflow. It remains a Kaggle-runtime secret and is attached only by the private Kaggle deployment notebook.
