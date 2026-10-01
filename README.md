# Tiny11 KVM runner probe

This public repository contains no credentials and no VM image. It only checks whether the GitHub-hosted runner assigned to a public repository exposes `/dev/kvm`.

If the probe passes, the private `lalibano/tiny11-kaggle-qemu` project can use the same runner class for the Tiny11 image build. If it fails, the remaining no-cost fallback is a time-bounded TCG build.
