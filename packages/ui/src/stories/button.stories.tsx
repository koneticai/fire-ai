import type { Meta, StoryObj } from '@storybook/react';
import { Button } from '../atoms/Button';
const meta: Meta<typeof Button> = { title: 'Atoms/Button', component: Button };
export default meta;
export const Primary: StoryObj<typeof Button> = { args: { children: 'Primary', variant: 'primary' } };
export const Secondary: StoryObj<typeof Button> = { args: { children: 'Secondary', variant: 'secondary' } };
