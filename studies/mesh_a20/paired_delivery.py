"""Installed current Agent/Tmux owners through a candidate shared launcher."""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path


async def run(args):
    from mesh_plus.api import Bridge, Client, Endpoint, Reader, ReadGuard
    from mesh_plus.transport import IPCServer, boottime_ms, connect_ipc
    from mesh_plus.testing.ssh_carrier import ssh_server

    selection = json.loads((Path.home() / ".local/share/chezmoi/deployments/tmux-observer.json").read_text())
    tmux_root = Path.home() / selection["core"]["prefix"]
    verified = 0
    for name, expected in selection["core"]["files"].items():
        if name.startswith("tmux_observer/") and name.endswith(".py"):
            if hashlib.sha256((tmux_root / name).read_bytes()).hexdigest() != expected["sha256"]:
                raise ValueError("selected_tmux_owner_bytes")
            verified += 1
    sys.path.insert(0, str(tmux_root))
    from agent_observer.mesh_publisher import make_publisher as agent_factory
    from tmux_observer.mesh_publisher import make_publisher as tmux_factory
    sources = {"agent": ("agent", agent_factory, "/run/user/1000/agent-observer/read.sock"),
               "tmux_default": ("tmux", tmux_factory, "/run/user/1000/tmux-observer/owner.sock")}
    reports = []
    with tempfile.TemporaryDirectory(prefix=".agent-a20-pair-", dir=Path.home()) as directory:
        root = Path(directory)
        launcher = root / "mesh-plus"
        original = (Path.home() / ".local/bin/mesh-plus").read_text()
        old = "/.local/share/agent-observer/" + (args.binding_prefix or
            "0.7.0a1-07196b5445766002-mesh-a17-system") + "/"
        new = "/.local/share/agent-observer/" + args.prefix.name + "/"
        if args.live_launcher:
            binding = old if args.binding_prefix else new
            if original.count(binding) != 2:
                raise ValueError("selected_shared_launcher_binding")
            launcher.write_text(original)
        else:
            if original.count(old) != 2:
                raise ValueError("captured_shared_launcher_binding")
            launcher.write_text(original.replace(old, new))
        launcher.chmod(0o755)
        config = root / "config/mesh-plus/sources.toml"
        config.parent.mkdir(parents=True, mode=0o700)
        config.write_text(f'version=1\nhost={json.dumps(args.host)}\n' + "".join(
            f'[sources.{source}]\ndomain="{domain}"\nsocket="{socket}"\n'
            for source, (domain, _, socket) in sources.items()))
        config.chmod(0o600)
        for source, (domain, factory, socket) in sources.items():
            publisher = factory(args.host, source, socket)
            path = root / (source + ".sock")
            server = await IPCServer(path, Bridge(publisher).serve).start()
            clients = []
            codec = publisher.state_profile.bind(args.host, source)

            async def exercise(connect, remote):
                async def revision():
                    return "sha256:" + "c" * 64
                reader = Reader(domain, [Endpoint(args.host, not remote, None if not remote else
                    "sha256:" + "b" * 64, connect, codec)], local_host="paired-client" if remote else args.host,
                    catalog_revision=None if not remote else "sha256:" + "c" * 64,
                    catalog_check=None if not remote else revision, profile=publisher.state_profile)
                snapshot = await reader.snapshot()
                host = snapshot["mesh"]["hosts"][0]
                if host["delivery"]["status"] != "ready":
                    raise ValueError("paired_snapshot_not_ready")
                stream = reader.watch(request_id="a" * 32, proof_interval=.2)
                guard = ReadGuard(domain, "a" * 32, profile=publisher.state_profile)
                try:
                    async with asyncio.timeout(20):
                        async for frame in stream:
                            guard.accept(frame)
                            if frame["mesh"]["hosts"][0]["delivery"]["status"] == "ready":
                                rows = guard.current(boottime_ms(), frame["mesh"]["reader"]["clock"])
                                break
                finally:
                    guard.disconnect()
                    await stream.aclose()
                if reader.inspect()["activeConnections"] or reader.inspect()["cleanupFailures"]:
                    raise ValueError("paired_cleanup")
                reports.append({"domain": domain, "carrier": "owned-fixed-ssh" if remote else "ipc",
                    "profile": publisher.profile, "snapshotRows": len(snapshot["sessions"]),
                    "currentWatchRows": len(rows), "proof": host["delivery"]["proof"] is not None,
                    "connectionsAfter": 0})

            async def local():
                client = await Client.connect(await connect_ipc(path), host=args.host, source=source,
                    profile=publisher.profile, codec=publisher.validate)
                clients.append(client)
                return client

            try:
                await exercise(local, False)
                ssh_root = root / (source + "-ssh")
                ssh_root.mkdir(mode=0o700)
                dispatcher = ssh_root / "fixed-command"
                dispatcher.write_text(f'''#!{args.prefix}/bin/python
import os,shlex
argv=shlex.split(os.environ['SSH_ORIGINAL_COMMAND'])
fixed=['mesh-plus','bridge','--source',{source!r},'--stdio']
assert len(argv)==10 and argv[:2]==['sh','-c'] and argv[3]=='mesh-plus-reached'
assert argv[4]=='b'*32 and argv[5:]==fixed
env={{**os.environ,'XDG_CONFIG_HOME':{str(root / 'config')!r}}}
os.execve({str(launcher)!r},fixed,env)
''')
                dispatcher.chmod(0o755)
                async with ssh_server(ssh_root, [str(dispatcher)], source) as channel:
                    async def remote():
                        client = await Client.connect(await channel(), host=args.host, source=source,
                            profile=publisher.profile, codec=publisher.validate)
                        clients.append(client)
                        return client
                    await exercise(remote, True)
                if not all(c.channel.closed for c in clients):
                    raise ValueError("paired_channel_retirement")
            finally:
                await server.close()
    return {"status": "passed", "host": args.host, "tmuxVersion": selection["core"]["version"],
            "tmuxOwnerFilesVerified": verified, "carriers": reports,
            "normalSelectionsChanged": False, "providerActions": 0,
            "limits": ["cached current owners", "owned localhost SSH; ordinary cross-host gate follows",
                       "no GUI/action or native collection proof"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=("snap", "starship"), required=True)
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--live-launcher", action="store_true")
    parser.add_argument("--binding-prefix")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args)), indent=2))
