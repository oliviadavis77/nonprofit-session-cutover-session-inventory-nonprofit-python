from __future__ import annotations

import argparse
import json

from session_inventory import client_from_environment


def main() -> None:
    parser = argparse.ArgumentParser(description="Keep one nonprofit operator session active.")
    parser.add_argument("user_id")
    args = parser.parse_args()
    inventory = client_from_environment().secure_inventory(args.user_id)
    print(json.dumps({"active": [s.session_id for s in inventory.active], "revoked": list(inventory.revoked)}))


if __name__ == "__main__":
    main()
