import type { ComponentType, SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Base({ size = 16, children, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

export function IconSearch(props: IconProps) {
  return (
    <Base {...props}>
      <circle cx="7" cy="7" r="4.4" />
      <path d="M10.3 10.3 13.6 13.6" />
    </Base>
  );
}

export function IconMic(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="6" y="1.6" width="4" height="7" rx="2" />
      <path d="M3.6 7.4a4.4 4.4 0 0 0 8.8 0M8 11.8v2.6M5.8 14.4h4.4" />
    </Base>
  );
}

export function IconCamera(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M1.8 5.2h2.4l1.1-1.7h5.4l1.1 1.7h2.4v8.1H1.8z" />
      <circle cx="8" cy="9.2" r="2.4" />
    </Base>
  );
}

export function IconCart(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M1.6 2.2h1.8l1.6 7.6h7.2l1.4-5.4H4.2" />
      <circle cx="6" cy="12.6" r="1" />
      <circle cx="11.6" cy="12.6" r="1" />
    </Base>
  );
}

export function IconUser(props: IconProps) {
  return (
    <Base {...props}>
      <circle cx="8" cy="5" r="2.6" />
      <path d="M2.8 14c0-2.6 2.3-4.2 5.2-4.2s5.2 1.6 5.2 4.2" />
    </Base>
  );
}

export function IconPin(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M8 14.4s4.6-4.1 4.6-7.4a4.6 4.6 0 1 0-9.2 0C3.4 10.3 8 14.4 8 14.4z" />
      <circle cx="8" cy="6.8" r="1.6" />
    </Base>
  );
}

export function IconAssistant(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M2 3.4h12v7.4H7.4L4.2 13.4v-2.6H2z" />
      <path d="M5.4 6.6h5.2M5.4 8.6h3.2" />
    </Base>
  );
}

export function IconInventory(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M2 4.2 8 1.8l6 2.4-6 2.4z" />
      <path d="M2 4.2v7.6L8 14.2l6-2.4V4.2M8 6.6v7.6" />
      <path d="M10.8 8.1h1.5" />
    </Base>
  );
}

export function IconPrice(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M8.4 1.9h4.2l1.5 1.5v4.2l-6.2 6.2a1.2 1.2 0 0 1-1.7 0L2.2 9.8a1.2 1.2 0 0 1 0-1.7z" />
      <circle cx="10.7" cy="5.3" r="1" />
    </Base>
  );
}

export function IconChart(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M2 13.6h12" />
      <path d="M3.6 13.6V8.4M7.2 13.6V4.6M10.8 13.6V9.8M14.4 13.6V6.2" />
    </Base>
  );
}

export function IconShield(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M8 1.8 13.2 4v4.1c0 3.2-2.2 5.4-5.2 6.3-3-.9-5.2-3.1-5.2-6.3V4z" />
      <path d="m5.7 8 1.7 1.7 3.1-3.2" />
    </Base>
  );
}

export function IconSegments(props: IconProps) {
  return (
    <Base {...props}>
      <circle cx="5.6" cy="5.2" r="2.2" />
      <path d="M1.8 13.4c0-2.2 1.7-3.6 3.8-3.6s3.8 1.4 3.8 3.6" />
      <circle cx="11.6" cy="6.1" r="1.8" />
      <path d="M9.4 13.4c0-1.8 1.3-3 2.9-3 1.5 0 2.6 1 2.6 2.6" />
    </Base>
  );
}

export function IconBackoffice(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="2" y="2.2" width="12" height="11.6" rx="1.2" />
      <path d="M2 6.2h12M5.4 6.2v7.6M10.6 6.2v7.6" />
    </Base>
  );
}

export function IconGrid(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="2.2" y="2.2" width="4.6" height="4.6" />
      <rect x="9.2" y="2.2" width="4.6" height="4.6" />
      <rect x="2.2" y="9.2" width="4.6" height="4.6" />
      <rect x="9.2" y="9.2" width="4.6" height="4.6" />
    </Base>
  );
}

export function IconList(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M2.2 4h11.6M2.2 8h11.6M2.2 12h11.6" />
    </Base>
  );
}

export function IconClose(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M3.6 3.6 12.4 12.4M12.4 3.6 3.6 12.4" />
    </Base>
  );
}

export function IconPlus(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M8 3.2v9.6M3.2 8h9.6" />
    </Base>
  );
}

export function IconCheck(props: IconProps) {
  return (
    <Base {...props}>
      <path d="m2.8 8.4 3.2 3.2 7.2-7.2" />
    </Base>
  );
}

export function IconArrowBack(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M13 8H3M7.2 3.8 3 8l4.2 4.2" />
    </Base>
  );
}

export function IconChevron(props: IconProps) {
  return (
    <Base {...props}>
      <path d="m4 6 4 4 4-4" />
    </Base>
  );
}

export function IconPhone(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="4.4" y="1.4" width="7.2" height="13.2" rx="1.4" />
      <path d="M7 12.6h2" />
    </Base>
  );
}

export function IconHeadphones(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M2.2 9.4V8a5.8 5.8 0 0 1 11.6 0v1.4" />
      <rect x="1.4" y="9" width="3" height="4.2" rx="1" />
      <rect x="11.6" y="9" width="3" height="4.2" rx="1" />
    </Base>
  );
}

export function IconLaptop(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="2.6" y="3.2" width="10.8" height="7.2" rx=".8" />
      <path d="M1.2 12.4h13.6" />
    </Base>
  );
}

export function IconAccessory(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M4.4 2.6h7.2v3.2a3.6 3.6 0 0 1-7.2 0z" />
      <path d="M8 9.4v3.4M5.4 13.4h5.2" />
    </Base>
  );
}

export function IconScreen(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="1.8" y="3" width="12.4" height="7.6" rx=".8" />
      <path d="M6 13.4h4" />
    </Base>
  );
}

export function IconStorage(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="2.2" y="3.4" width="11.6" height="9.2" rx="1" />
      <path d="M5 6.4v3.2M8 6.4v3.2M11 6.4v3.2" />
    </Base>
  );
}

export function IconMemory(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="2" y="5" width="12" height="6" rx=".8" />
      <path d="M5 11v2M8 11v2M11 11v2M5 3v2M8 3v2M11 3v2" />
    </Base>
  );
}

export function IconConnectivity(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M2 13.4 6.2 2.6l3 7.4 2-3.2 1.6 6.6" />
    </Base>
  );
}

export function IconBattery(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="1.6" y="5.2" width="11" height="5.6" rx="1" />
      <path d="M14.2 7v2" />
      <path d="M4 7.4v1.2M6.4 7.4v1.2" />
    </Base>
  );
}

export function IconFeature(props: IconProps) {
  return (
    <Base {...props}>
      <path d="m8 1.8 1.9 3.9 4.3.6-3.1 3 .7 4.3L8 11.6l-3.8 2 .7-4.3-3.1-3 4.3-.6z" />
    </Base>
  );
}

export function IconTag(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M2 2h5.6l6.4 6.4-5.6 5.6L2 7.6z" />
      <circle cx="5" cy="5" r=".9" />
    </Base>
  );
}

export const ATTRIBUTE_ICONS: Record<string, ComponentType<IconProps>> = {
  brand: IconTag,
  screen: IconScreen,
  storage: IconStorage,
  memory: IconMemory,
  connectivity: IconConnectivity,
  battery: IconBattery,
  feature: IconFeature,
};

export const CATEGORY_ICONS: Record<string, ComponentType<IconProps>> = {
  phones: IconPhone,
  headphones: IconHeadphones,
  laptops: IconLaptop,
  accessories: IconAccessory,
};
