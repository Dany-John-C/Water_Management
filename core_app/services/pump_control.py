class PumpController:
    def __init__(self):
        self.state = "off"
        self.mode = "auto"  # 'auto' or 'manual'
        self.moisture_threshold_low = 30.0  # Turn ON below 30%
        self.moisture_threshold_high = 70.0 # Turn OFF above 70%

    def evaluate_auto_irrigation(self, soil_moisture):
        """Called automatically when a new sensor reading arrives."""
        if self.mode != "auto":
            return

        if soil_moisture < self.moisture_threshold_low and self.state == "off":
            self.state = "on"
            print(f"[Auto-Irrigation] Soil moisture dropped to {soil_moisture}%. Turning pump ON.")
        elif soil_moisture > self.moisture_threshold_high and self.state == "on":
            self.state = "off"
            print(f"[Auto-Irrigation] Soil moisture reached {soil_moisture}%. Turning pump OFF.")

    def manual_override(self, new_state):
        """Called when a user clicks the button on the dashboard."""
        self.state = new_state
        self.mode = "manual"  # Temporarily disable auto so user stays in control
        print(f"[Pump Override] Manual override engaged. Pump set to: {new_state}")

    def reset_to_auto(self):
        self.mode = "auto"
        print("[Pump Control] Mode reset to AUTO.")

pump_controller = PumpController()
