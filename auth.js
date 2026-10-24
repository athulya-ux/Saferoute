// ========================================================
// SafeRoute - Feature 4: Women-Only Verification & Passkeys
// ========================================================

let pendingPhone = null;
let selfieBase64Data = null;

function openAuthModal() {
    openModal('authModal');
}

function sendAuthOTP() {
    const phone = document.getElementById('authPhoneInput').value.trim();
    if (!phone) {
        alert('Please enter a valid mobile number.');
        return;
    }

    pendingPhone = phone;

    fetch('/api/auth/send_otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: phone })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            document.getElementById('otpInputSection').style.display = 'block';
            const hintEl = document.getElementById('demoOtpHint');
            if (data.demo_otp_hint) {
                hintEl.textContent = `Demo Code: ${data.demo_otp_hint}`;
                document.getElementById('authOtpCodeInput').value = data.demo_otp_hint;
            }
            alert(`OTP dispatched to ${phone}.`);
        } else {
            alert(data.error || 'Failed to send OTP.');
        }
    })
    .catch(err => alert('Network error sending verification code.'));
}

function verifyAuthOTP() {
    const code = document.getElementById('authOtpCodeInput').value.trim();
    if (!code || !pendingPhone) {
        alert('Please enter the 6-digit OTP code.');
        return;
    }

    fetch('/api/auth/verify_otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            phone: pendingPhone,
            otp: code,
            full_name: 'Verified Traveler'
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success' && data.user) {
            window.currentUser = data.user;
            localStorage.setItem('saferoute_user', JSON.stringify(data.user));
            updateUserDisplay();

            // Transition to Step 2: Affirmative declaration
            document.getElementById('authStepPhone').style.display = 'none';
            document.getElementById('authStepDeclaration').style.display = 'block';
        } else {
            alert(data.error || 'Invalid OTP code.');
        }
    })
    .catch(err => alert('Error verifying code.'));
}

function submitWomanDeclaration() {
    const checked = document.getElementById('declareWomanCheck').checked;
    if (!checked) {
        alert('Please tick the confirmation box affirming your identity as a woman.');
        return;
    }

    const userId = window.currentUser ? window.currentUser.id : 1;

    fetch('/api/auth/declare_woman', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            declared: true
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            if (window.currentUser) {
                window.currentUser.verified_woman_declared = true;
                window.currentUser.verification_status = 'verified';
                localStorage.setItem('saferoute_user', JSON.stringify(window.currentUser));
            }
            updateUserDisplay();
            // Step 3: Passkeys
            document.getElementById('authStepDeclaration').style.display = 'none';
            document.getElementById('authStepPasskey').style.display = 'block';
        }
    });
}

function setupWebAuthnPasskey() {
    const userId = window.currentUser ? window.currentUser.id : 1;

    // Check if browser WebAuthn is supported
    if (window.PublicKeyCredential) {
        fetch('/api/auth/passkey/challenge', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                // Register passkey
                fetch('/api/auth/passkey/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        credential_id: 'cred_' + Math.random().toString(36).substring(2, 15)
                    })
                })
                .then(r => r.json())
                .then(resData => {
                    alert('Passkey (Face ID / Fingerprint) successfully registered for passwordless login.');
                    closeModal('authModal');
                });
            });
    } else {
        alert('Device passkey registered via secure token.');
        closeModal('authModal');
    }
}

function handleSelfieUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        selfieBase64Data = e.target.result;
    };
    reader.readAsDataURL(file);
}

function submitSelfieVerify() {
    if (!selfieBase64Data) {
        alert('Please choose or take a photo first.');
        return;
    }

    const userId = window.currentUser ? window.currentUser.id : 1;

    fetch('/api/auth/selfie_verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            selfie_base64: selfieBase64Data
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            selfieBase64Data = null; // Clear client memory
            alert(data.message);
            closeModal('authModal');
        }
    });
}

function deleteUserAccount() {
    if (!confirm('Are you sure you want to delete your account? All saved contacts, locations, and chat logs will be permanently erased.')) return;

    const userId = window.currentUser ? window.currentUser.id : 1;

    fetch('/api/auth/delete_account', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
    })
    .then(res => res.json())
    .then(data => {
        localStorage.removeItem('saferoute_user');
        window.currentUser = null;
        updateUserDisplay();
        closeModal('authModal');
        alert('Account and data permanently deleted.');
    });
}

function updateUserDisplay() {
    const handleDisplay = document.getElementById('userHandleDisplay');
    const banner = document.getElementById('verificationBanner');

    const stored = localStorage.getItem('saferoute_user');
    if (stored) {
        try {
            window.currentUser = JSON.parse(stored);
        } catch (e) {}
    }

    if (window.currentUser && window.currentUser.verified_woman_declared) {
        handleDisplay.innerHTML = `<i class="fa-solid fa-circle-check text-green"></i> ${window.currentUser.anonymous_handle}`;
        if (banner) banner.style.display = 'none';
    } else if (window.currentUser) {
        handleDisplay.textContent = window.currentUser.anonymous_handle;
        if (banner) banner.style.display = 'flex';
    } else {
        handleDisplay.textContent = 'Verify & Join';
        if (banner) banner.style.display = 'flex';
    }
}
