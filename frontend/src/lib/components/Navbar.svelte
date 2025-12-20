<script lang="ts">
    import { page } from "$app/state";

    interface NavItem {
        name: string;
        href: string;
    }

    const navItems: NavItem[] = [
        { name: "Dashboard", href: "/" },
        { name: "New Run", href: "/create" },
        { name: "Queue", href: "/jobs" },
        { name: "Analysis", href: "/analysis" },
    ];

    function isActive(href: string) {
        if (href === "/") return page.url.pathname === "/";
        return page.url.pathname.startsWith(href);
    }
</script>

<div
    class="navbar bg-base-200 border-b border-base-300 px-4 sticky top-0 z-50 backdrop-blur-md bg-opacity-80"
>
    <div class="flex-1">
        <a
            href="/"
            class="btn btn-ghost text-xl font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent"
        >
            jam master user
        </a>
    </div>
    <div class="flex-none">
        <ul class="menu menu-horizontal px-1 gap-2">
            {#each navItems as item: NavItem}
                <li>
                    <a
                        href={item.href}
                        class={isActive(item.href)
                            ? "active font-semibold"
                            : ""}
                    >
                        {item.name}
                    </a>
                </li>
            {/each}
        </ul>
    </div>
</div>
