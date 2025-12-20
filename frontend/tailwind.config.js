/** @type {import('tailwindcss').Config} */
export default {
    content: ['./src/**/*.{html,js,svelte,ts}'],
    theme: {
        extend: {
            colors: {
                "retro-bg": "#008080",
                "retro-gray": "#c0c0c0",
                "retro-dark-gray": "#808080",
                "retro-blue": "#000080",
                "retro-light": "#ffffff",
                "retro-shadow": "#404040",
                "primary": "#000080",
                "win-magenta": "#ff0080",
                "win-purple": "#8000ff",
            },
            fontFamily: {
                "mono": ["Space Mono", "monospace"],
                "pixel": ["VT323", "monospace"],
                "display": ["Space Mono", "monospace"],
            },
            boxShadow: {
                'retro-out': '2px 2px 0px #404040, -2px -2px 0px #ffffff',
                'retro-in': 'inset 2px 2px 0px #404040, inset -2px -2px 0px #ffffff',
                'retro-raised': 'inset 1px 1px 0px #ffffff, inset -1px -1px 0px #000000, 2px 2px 0px #000000',
                'retro-flat': '2px 2px 0px #000000',
            }
        },
    },
    plugins: [
        require('daisyui'),
        require('@tailwindcss/typography'),
    ],
    daisyui: {
        themes: [
            {
                retro: {
                    "primary": "#000080",
                    "secondary": "#ff0080",
                    "accent": "#8000ff",
                    "neutral": "#d4d0c8",
                    "base-100": "#d4d0c8",
                    "info": "#000080",
                    "success": "#008000",
                    "warning": "#808000",
                    "error": "#800000",
                },
            },
            "dark",
            "light"
        ],
    },
}
