import { vi } from 'vitest';

vi.mock('obsidian', () => ({
    Plugin: class {},
    Notice: class { setMessage() {} },
    ItemView: class {},
    Modal: class { onOpen() {} onClose() {} close() {} },
    Setting: class { setName() { return this; } setDesc() { return this; } addText() { return this; } addButton() { return this; } addDropdown() { return this; } addToggle() { return this; } },
    PluginSettingTab: class { display() {} },
    addIcon: () => {},
}));
