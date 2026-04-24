// Simple Notification Sound Manager - Plays once, no looping
class SimpleNotificationSound {
    constructor() {
        this.audio = null;
        this.enabled = this.getSoundPreference();
        this.isPlaying = false;
        this.initSound();
        this.setupUnlock();
    }

    initSound() {
        try {
            this.audio = new Audio('/static/sounds/notification.mp3');
            this.audio.preload = 'auto';
            this.audio.volume = 0.7;
            this.audio.loop = false;
            
            // Reset flag when sound ends
            this.audio.onended = () => {
                console.log('✅ Sound finished');
                this.isPlaying = false;
            };
            
            console.log('🎵 Audio object created');
        } catch(e) {
            console.log('❌ Error creating audio:', e);
            this.audio = null;
        }
    }

    setupUnlock() {
        const unlock = () => {
            if (this.audioUnlocked) return;
            
            if (this.audio) {
                this.audio.volume = 0;
                this.audio.loop = false;
                this.audio.play().then(() => {
                    this.audio.pause();
                    this.audio.currentTime = 0;
                    this.audio.volume = 0.7;
                    this.audioUnlocked = true;
                    console.log('✅ Audio unlocked!');
                }).catch(e => {
                    console.log('Unlock failed');
                });
            }
        };
        
        document.addEventListener('click', unlock);
        document.addEventListener('touchstart', unlock);
    }

    play() {
        console.log('🔔 play() called, enabled:', this.enabled, 'isPlaying:', this.isPlaying);
        
        if (!this.enabled) {
            console.log('🔇 Sound disabled');
            return;
        }
        
        // Don't play if sound is already playing
        if (this.isPlaying) {
            console.log('⚠️ Sound already playing, skipping');
            return;
        }
        
        this.isPlaying = true;
        
        if (this.audio) {
            try {
                this.audio.pause();
                this.audio.currentTime = 0;
                this.audio.loop = false;
                
                const playPromise = this.audio.play();
                if (playPromise !== undefined) {
                    playPromise.then(() => {
                        console.log('✅ SOUND PLAYING ONCE!');
                    }).catch(error => {
                        console.log('Play failed:', error);
                        this.isPlaying = false;
                        this.playBeep();
                    });
                }
            } catch(e) {
                this.isPlaying = false;
                this.playBeep();
            }
        } else {
            this.playBeep();
        }
    }

    playBeep() {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            const ctx = new AudioContext();
            const oscillator = ctx.createOscillator();
            const gain = ctx.createGain();
            
            oscillator.connect(gain);
            gain.connect(ctx.destination);
            
            oscillator.frequency.value = 880;
            gain.gain.value = 0.2;
            
            oscillator.start();
            gain.gain.exponentialRampToValueAtTime(0.00001, ctx.currentTime + 0.5);
            oscillator.stop(ctx.currentTime + 0.5);
            
            if (ctx.state === 'suspended') {
                ctx.resume();
            }
            console.log('✅ BEEP PLAYED ONCE!');
            
            setTimeout(() => {
                this.isPlaying = false;
            }, 600);
        } catch(e) {
            console.log('Beep failed:', e);
            this.isPlaying = false;
        }
    }

    getSoundPreference() {
        const saved = localStorage.getItem('notification_sound_enabled');
        return saved === null ? true : saved === 'true';
    }

    toggle() {
        this.enabled = !this.enabled;
        localStorage.setItem('notification_sound_enabled', this.enabled);
        console.log('🔊 Sound toggled to:', this.enabled);
        if (this.enabled) {
            this.play();
        }
        return this.enabled;
    }
}

// Initialize
window.notificationSound = new SimpleNotificationSound();

function playNotificationSound() {
    if (window.notificationSound) {
        window.notificationSound.play();
    }
}

window.testSound = function() {
    playNotificationSound();
};

console.log('✅ notification_sound.js loaded - No Looping!');