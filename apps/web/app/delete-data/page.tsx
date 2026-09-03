import type { Metadata } from "next";

import BrandHeader from "../../components/BrandHeader";
import DeleteDataForm from "../../components/DeleteDataForm";
import styles from "../legal.module.css";

export const metadata: Metadata = {
  title: "Delete Your Data — Parent Health Agent",
  description: "Request deletion of your family's health records from Parent Health Agent.",
};

export default function DeleteDataPage() {
  return (
    <main className={styles.page}>
      <div className={styles.shell}>
        <BrandHeader />

        <section className={styles.card}>
          <span className={styles.eyebrow}>Data deletion</span>
          <h1>Delete your family&apos;s data</h1>

          <div className={styles.prose}>
            <p>
              You can ask us to permanently delete your family&apos;s records — names, phone
              numbers, and any health answers recorded during setup.
            </p>

            <h2>Identity verification required</h2>
            <p>
              Because these records include another person&apos;s health information, we
              can&apos;t act on a deletion request until we&apos;ve verified it&apos;s coming
              from someone entitled to make it. Specifically, we require:
            </p>
            <ul>
              <li>
                The request to come from the <strong>same WhatsApp number</strong> already on
                the family record (either the parent&apos;s or the registering family
                member&apos;s), or
              </li>
              <li>
                If that&apos;s not possible, enough detail for us to confirm your identity
                and relationship to the family record before we proceed.
              </li>
            </ul>
            <p>
              We&apos;ll always follow up over WhatsApp to the number on file to confirm
              before deleting anything — this protects the other family member too, since one
              person alone shouldn&apos;t be able to erase shared family data without the
              other side being aware.
            </p>

            <h2>What happens after you submit</h2>
            <p>
              The form below opens a pre-filled email to our support address. Reply from an
              address you control, and we&apos;ll verify your identity as described above
              before deleting anything. This is a manual process for now — we don&apos;t yet
              have self-serve deletion built into the product.
            </p>
          </div>

          <DeleteDataForm />
        </section>
      </div>
    </main>
  );
}
