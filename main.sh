#!/bin/bash

# Script to set up SSH server on macOS for passwordless access
# Run this on your MacBook

# Exit on error
set -e

echo "Setting up SSH server on macOS for passwordless access..."

# Enable Remote Login if not already enabled
if [ "$(sudo systemsetup -getremotelogin)" != "Remote Login: On" ]; then
    echo "Enabling Remote Login..."
    sudo systemsetup -setremotelogin on
else
    echo "Remote Login already enabled."
fi

# Create SSH directory if it doesn't exist
if [ ! -d "$HOME/.ssh" ]; then
    echo "Creating .ssh directory..."
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
fi

# Create authorized_keys file if it doesn't exist
if [ ! -f "$HOME/.ssh/authorized_keys" ]; then
    echo "Creating authorized_keys file..."
    touch "$HOME/.ssh/authorized_keys"
    chmod 600 "$HOME/.ssh/authorized_keys"
fi

# Generate an SSH key pair for your phone to use
echo "Generating an SSH key pair..."
ssh-keygen -t ed25519 -f "$HOME/phone_key" -N ""

# Show the private key (to be copied to your phone)
echo -e "\n\n========== PRIVATE KEY (COPY TO YOUR PHONE) =========="
cat "$HOME/phone_key"
echo -e "========== END OF PRIVATE KEY =========="

# Add the public key to authorized_keys
echo "Adding public key to authorized_keys..."
cat "$HOME/phone_key.pub" >> "$HOME/.ssh/authorized_keys"

# Configure SSH server for better security
echo "Configuring SSH server..."
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
sudo tee /etc/ssh/sshd_config > /dev/null << EOF
Port 22
Protocol 2
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key
UsePrivilegeSeparation yes
KeyRegenerationInterval 3600
ServerKeyBits 1024
SyslogFacility AUTH
LogLevel INFO
LoginGraceTime 120
PermitRootLogin no
StrictModes yes
RSAAuthentication yes
PubkeyAuthentication yes
IgnoreRhosts yes
RhostsRSAAuthentication no
HostbasedAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no
PasswordAuthentication no
X11Forwarding yes
X11DisplayOffset 10
PrintMotd no
PrintLastLog yes
TCPKeepAlive yes
AcceptEnv LANG LC_*
Subsystem sftp /usr/libexec/sftp-server
UsePAM yes
EOF

# Restart SSH service
echo "Restarting SSH service..."
sudo launchctl unload /System/Library/LaunchDaemons/ssh.plist
sudo launchctl load /System/Library/LaunchDaemons/ssh.plist

# Get and display IP address
IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}')
echo -e "\n\nSSH setup complete!"
echo "Your MacBook's IP address is: $IP"
echo "To connect from your phone, you'll need:"
echo "1. An SSH client app (like Termius, JuiceSSH, etc.)"
echo "2. Copy the PRIVATE KEY shown above to your phone's SSH client"
echo "3. Connect to $IP using your macOS username: $(whoami)"
echo "4. Keep this private key secure and don't share it"
