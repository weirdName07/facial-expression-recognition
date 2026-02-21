/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./src/**/*.{html,ts}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                mono: ['JetBrains Mono', 'Menlo', 'monospace']
            },
            colors: {
                dark: {
                    900: '#0f172a',
                    800: '#1e293b'
                }
            }
        },
    },
    plugins: [],
}
