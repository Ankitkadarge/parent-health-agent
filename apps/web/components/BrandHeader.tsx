import Link from "next/link";

import styles from "../app/legal.module.css";

export default function BrandHeader() {
  return (
    <Link className={styles.brand} href="/" aria-label="Back to Parent Health Agent">
      <span className={styles.brandMark} aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" width="22" height="22">
          <path
            d="M12 3c2.8 3.2 4.7 5.8 4.7 8.5A4.7 4.7 0 0 1 12 16.2a4.7 4.7 0 0 1-4.7-4.7C7.3 8.8 9.2 6.2 12 3Z"
            fill="currentColor"
          />
          <path
            d="M7 18.2c1.5 1.4 3.2 2.1 5 2.1s3.5-.7 5-2.1"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
          />
        </svg>
      </span>
      <span>Parent Health Agent</span>
    </Link>
  );
}
