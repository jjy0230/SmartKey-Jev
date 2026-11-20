"""
SmartKey-Jev Main Entrypoint.
Runs the resident desktop background daemon.
"""

import sys
import argparse
from smartkey_jev.app import SmartKeyApp
from smartkey_jev.core.config import AppConfig, HotkeyConfig, ModelConfig, UIConfig


def parse_args():
    parser = argparse.ArgumentParser(description="SmartKey-Jev: Desktop Instant Intent Predictor & Dynamic Shortcut Dispatcher")
    parser.add_argument("--hotkey", type=str, default="double_alt", choices=["double_alt", "double_ctrl", "alt_space"], help="Trigger hotkey type")
    parser.add_argument("--enable-model", action="store_true", help="Enable neural intent model prediction")
    parser.add_argument("--model-provider", type=str, default="stub", choices=["stub", "openai_compatible", "http"], help="Model provider")
    parser.add_argument("--model-url", type=str, default="http://127.0.0.1:8000/v1/intent", help="Model endpoint URL")
    parser.add_argument("--opacity", type=float, default=0.92, help="Floating card window opacity")
    return parser.parse_args()


def main():
    args = parse_args()
    config = AppConfig(
        hotkey=HotkeyConfig(trigger_type=args.hotkey),
        model=ModelConfig(
            enabled=args.enable_model,
            provider=args.model_provider,
            endpoint_url=args.model_url,
        ),
        ui=UIConfig(opacity=args.opacity),
    )

    print("=================================================================")
    print("   SmartKey-Jev: Desktop Instant Intent Predictor Daemon")
    print(f"   Hotkey: {config.hotkey.trigger_type} | Model Enabled: {config.model.enabled}")
    print("=================================================================")

    app = SmartKeyApp(config)
    app.run()


if __name__ == "__main__":
    main()
