import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

interface User {
    id: number
    email: string
    full_name: string
}

export const useAuthStore = defineStore('auth', () => {
    const token = ref<string | null>(localStorage.getItem('token'))
    const user = ref<User | null>(JSON.parse(localStorage.getItem('user') || 'null'))

    const isAuthenticated = computed(() => !!token.value)

    async function login(email: string, password: string) {
        // Backend's OAuth2 login expects application/x-www-form-urlencoded.
        const body = new URLSearchParams()
        body.append('username', email)
        body.append('password', password)

        const response = await fetch('http://localhost:8000/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body,
        })

        if (!response.ok) {
            const error = await response.json().catch(() => ({}))
            throw new Error(error.detail || 'Login failed')
        }

        const data = await response.json()
        token.value = data.access_token
        localStorage.setItem('token', data.access_token)

        // The login response only carries the bearer token; fetch the user
        // record so we know id / email / full_name for routing and filing
        // filtering.
        const meResp = await fetch('http://localhost:8000/api/auth/me', {
            headers: { Authorization: `Bearer ${data.access_token}` },
        })
        if (meResp.ok) {
            const me = await meResp.json()
            user.value = {
                id: me.id,
                email: me.email,
                full_name: me.full_name || '',
            }
            localStorage.setItem('user', JSON.stringify(user.value))
        }
    }

    function logout() {
        token.value = null
        user.value = null
        localStorage.removeItem('token')
        localStorage.removeItem('user')
    }

    async function register(email: string, password: string, fullName: string) {
        const response = await fetch('http://localhost:8000/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                password,
                full_name: fullName,
            }),
        })

        if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || 'Registration failed')
        }
    }

    const mode = ref<string>('novice')

    function setMode(newMode: string) {
        mode.value = newMode
    }

    return {
        token,
        user,
        mode,
        isAuthenticated,
        login,
        register,
        logout,
        setMode
    }
})
