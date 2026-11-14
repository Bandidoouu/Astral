#!/usr/bin/env python
"""Entrenamiento contrastivo de ASTRAL (CLAUDE.md, secciones 8.2-8.3).

Ejemplos:
  # prueba rápida (pocos pasos)
  python -m ml.train --run smoke --epochs 1 --steps-per-epoch 20
  # corrida corta de H4
  python -m ml.train --run short60 --epochs 2
  # modelo principal y ablación
  python -m ml.train --run main60 --epochs 40 --version 1
  python -m ml.train --run abl60 --epochs 25 --no-disc

Log por época: pérdida contrastiva, pérdida y exactitud del discriminador
(con 2 cuerpos debe bajar hacia 50%), lambda, lr y std de los embeddings
(alarma de colapso: si tiende a 0, todos los embeddings son iguales).
"""
import argparse
import json
import math
import os
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.tensorboard import SummaryWriter

from ml.model.channels import make_views
from ml.model.dataset import BODY_ID, BalancedLoader, default_sources
from ml.model.net import AstralNet, nt_xent

ROOT = Path(os.environ.get("ASTRAL_ROOT", Path.home() / "astral"))


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", required=True, help="nombre de la corrida (runs/<run>)")
    p.add_argument("--scale", type=int, default=60)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--per-body", type=int, default=64,
                   help="parches por cuerpo por lote (2 cuerpos x 64 = 128 parches, 256 vistas)")
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--wd", type=float, default=0.05)
    p.add_argument("--warmup-epochs", type=float, default=0.5)
    p.add_argument("--temperature", type=float, default=0.1)
    p.add_argument("--lambda-max", type=float, default=1.0)
    p.add_argument("--disc-lr-mult", type=float, default=10.0)
    p.add_argument("--no-disc", action="store_true",
                   help="ablación: lambda = 0 (el discriminador solo mide, no empuja)")
    p.add_argument("--steps-per-epoch", type=int, default=None)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--version", type=int, default=None,
                   help="si se da, guarda data/artifacts/encoder_v{n}.pt al final")
    p.add_argument("--resume", action="store_true", help="seguir desde last.pt")
    p.add_argument("--log-every", type=int, default=50)
    return p.parse_args()


def lambda_schedule(progress, lam_max):
    """DANN: sube suave de 0 a lam_max con el progreso (0..1)."""
    return lam_max * (2.0 / (1.0 + math.exp(-10.0 * progress)) - 1.0)


def main():
    a = parse_args()
    torch.manual_seed(a.seed); np.random.seed(a.seed); random.seed(a.seed)
    torch.backends.cudnn.benchmark = True
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    dev = "cuda"

    sets = default_sources(a.scale, exclude_holdout=True)
    bodies = [s.body for s in sets]
    lut = torch.full((len(BODY_ID),), -1, dtype=torch.long)
    for i, b in enumerate(bodies):
        lut[BODY_ID[b]] = i
    lut = lut.to(dev)
    loader = BalancedLoader(sets, per_body=a.per_body, device=dev,
                            steps_per_epoch=a.steps_per_epoch, seed=a.seed)
    steps, total = len(loader), len(loader) * a.epochs
    print(f"cuerpos={bodies} parches={[len(s.idx) for s in sets]} "
          f"lote={a.per_body * len(sets)} pasos/época={steps} total={total}")

    model = AstralNet(n_bodies=len(sets)).to(dev).to(memory_format=torch.channels_last)
    disc_params = list(model.disc.parameters())
    disc_ids = {id(q) for q in disc_params}
    main_params = [q for q in model.parameters() if id(q) not in disc_ids]
    opt = torch.optim.AdamW([
        dict(params=main_params, lr=a.lr, weight_decay=a.wd),
        # el discriminador aprende más rápido para seguir siendo un rival útil
        dict(params=disc_params, lr=a.lr * a.disc_lr_mult, weight_decay=0.0)])
    warm = int(a.warmup_epochs * steps)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / max(1, warm) if s < warm
        else 0.5 * (1 + math.cos(math.pi * (s - warm) / max(1, total - warm))))

    run_dir = ROOT / "runs" / a.run
    ck_dir = ROOT / "data/artifacts/checkpoints" / a.run
    run_dir.mkdir(parents=True, exist_ok=True); ck_dir.mkdir(parents=True, exist_ok=True)
    start_epoch, gstep = 0, 0
    if a.resume and (ck_dir / "last.pt").exists():
        ck = torch.load(ck_dir / "last.pt", map_location=dev)
        model.load_state_dict(ck["model"]); opt.load_state_dict(ck["opt"])
        sched.load_state_dict(ck["sched"])
        start_epoch, gstep = ck["epoch"] + 1, ck["gstep"]
        print(f"reanudando desde época {start_epoch}")
    with open(run_dir / "config.json", "w") as f:
        json.dump(vars(a) | {"bodies": bodies, "steps_per_epoch": steps}, f, indent=2)
    tb = SummaryWriter(run_dir)
    chance = 100.0 / len(sets)

    for epoch in range(start_epoch, a.epochs):
        model.train()
        t0 = time.time()
        acc = dict(con=0.0, dis=0.0, hit=0, n=0, std=0.0)
        for i, (z, px, body) in enumerate(loader):
            progress = gstep / max(1, total)
            lam = 0.0 if a.no_disc else lambda_schedule(progress, a.lambda_max)
            with torch.no_grad():
                x = torch.cat([make_views(z, px), make_views(z, px)])
                x = x.contiguous(memory_format=torch.channels_last)
            y = lut[body].repeat(2)
            with torch.autocast("cuda", dtype=torch.bfloat16):
                emb, proj, logits = model(x, lam)
            B = z.shape[0]
            l_con = nt_xent(proj[:B].float(), proj[B:].float(), a.temperature)
            l_dis = F.cross_entropy(logits.float(), y)
            loss = l_con + l_dis   # la GRL ya escala por -lambda hacia el encoder
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step(); sched.step(); gstep += 1

            with torch.no_grad():
                hit = (logits.argmax(1) == y).sum().item()
                std = emb.float().std(0).mean().item()
            acc["con"] += l_con.item(); acc["dis"] += l_dis.item()
            acc["hit"] += hit; acc["n"] += len(y); acc["std"] += std
            if gstep % a.log_every == 0:
                tb.add_scalar("step/loss_contrastive", l_con.item(), gstep)
                tb.add_scalar("step/loss_disc", l_dis.item(), gstep)
                tb.add_scalar("step/disc_acc", 100 * hit / len(y), gstep)
                tb.add_scalar("step/lambda", lam, gstep)
                tb.add_scalar("step/lr", sched.get_last_lr()[0], gstep)
                print(f"  ep {epoch + 1} paso {i + 1}/{steps}  con={l_con.item():.3f} "
                      f"dis={l_dis.item():.3f} acc={100 * hit / len(y):.1f}% lam={lam:.3f}",
                      flush=True)

        n_it = i + 1
        rec = dict(epoch=epoch + 1, loss_contrastive=acc["con"] / n_it,
                   loss_disc=acc["dis"] / n_it, disc_acc=100 * acc["hit"] / acc["n"],
                   disc_chance=chance, lam=lam, lr=sched.get_last_lr()[0],
                   emb_std=acc["std"] / n_it, seconds=time.time() - t0)
        for k in ("loss_contrastive", "loss_disc", "disc_acc", "lam", "emb_std"):
            tb.add_scalar(f"epoch/{k}", rec[k], epoch + 1)
        with open(run_dir / "epochs.jsonl", "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[época {epoch + 1}/{a.epochs}] contrastiva={rec['loss_contrastive']:.4f}  "
              f"disc={rec['loss_disc']:.4f}  disc_acc={rec['disc_acc']:.1f}% "
              f"(azar {chance:.0f}%)  lambda={lam:.3f}  lr={rec['lr']:.2e}  "
              f"emb_std={rec['emb_std']:.4f}  {rec['seconds'] / 60:.1f} min", flush=True)

        torch.save(dict(model=model.state_dict(), opt=opt.state_dict(),
                        sched=sched.state_dict(), epoch=epoch, gstep=gstep, args=vars(a)),
                   ck_dir / "last.pt")
        torch.save(model.encoder.state_dict(), ck_dir / f"encoder_ep{epoch + 1:02d}.pt")

    if a.version is not None:
        out = ROOT / f"data/artifacts/encoder_v{a.version}.pt"
        torch.save(model.encoder.state_dict(), out)
        print("->", out)
    tb.close()


if __name__ == "__main__":
    main()
