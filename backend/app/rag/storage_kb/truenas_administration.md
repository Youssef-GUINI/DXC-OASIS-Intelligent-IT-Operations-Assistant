➤

1. [Documentation Hub](../../../../)
2. /
3. [TrueNAS 27 (Early)](../../../../scale/)
4. /
5. [Storage](../../../../scale/storage/)
6. /
7. [Pools](../../../../scale/storage/pools/)
8. /
9. Managing Pools

[Edit page](https://github.com/truenas/documentation/edit/master/content/SCALE/Storage/Pools/ManagePools.md)

> ![TrueNAS](../../../../favicon/TN-favicon-32x32.png "TrueNAS Development Documentation")TrueNAS Development Documentation
>
> This content follows experimental development changes in TrueNAS 27, a future version of TrueNAS.
> Use the **Product** and **Version** selectors above to view content specific to a stable software release.

# Managing Pools

15 minute read.

[Last Modified 2026-04-21 16:42 EDT](https://github.com/truenas/documentation/commit/5691846a424a101769a76b0bc65b1392338aa3e2 "DOCS-2494 / 27 / Docs 2494 investigate alias docs 404 s (#4555) (5691846a4)")

The **Storage Dashboard** widgets provide enhanced storage provisioning capabilities and access to pool management options to keep the pool and disks healthy, upgrade pools and VDEVs, open datasets, snapshots, and data protection screens.
This article provides instructions on pool management functions available in the TrueNAS UI.

[![Storage Dashboard with Pool](../../../../images/SCALE/Storage/StorageDashboardWithPool.png "Storage Dashboard with Pool")

[Figure 1: Storage Dashboard with Pool](#figure-1)](../../../../images/SCALE/Storage/StorageDashboardWithPool.png)

## Setting Up Auto TRIM

Select **Storage** on the main navigation panel to open the **Storage Dashboard**.
To see if the AutoTRIM function is enabled, locate the **Storage Health** widget for the pool.

To enable or disable the function, click on the more\_vert dropdown menu and select **AutoTRIM** to open the **Pool Options for *poolname*** dialog.

[![Pool Edit AutoTRIM Dialog](../../../../images/SCALE/Storage/PoolOptionsAutoTRIM.png "Pool Edit AutoTRIM Dialog")

[Figure 2: Pool Edit AutoTRIM Dialog](#figure-2)](../../../../images/SCALE/Storage/PoolOptionsAutoTRIM.png)

Select **Auto TRIM**.

Click **Save**.

With **Auto TRIM** selected and active, TrueNAS periodically checks the pool disks for storage blocks it can reclaim.
Auto TRIM can impact pool performance, so the default setting is disabled.

For more details about TRIM in ZFS, see the `autotrim` property description in [zpool.8](https://zfsonlinux.org/manpages/0.8.1/man8/zpool.8.html).

## Exporting or Deleting a Pool

Use the **Disconnect** button to delete or export a pool and transfer drives to a new system where you can import the pool.
Deleting the pool also deletes any data stored on it.

Backup critical data stored in the pool you intend to export or delete before performing these procedures!

Click on **Disconnect** for the pool on the **Storage Dashboard** to open the \**Disconnect *poolname** window.

### Exporting a Pool

After backing up critical data stored in the pool you plan to export, click **Disconnect** for the pool.

Click **Export Pool** in the \**Disconnect *poolname** window.

[![Export Pool Window](../../../../images/SCALE/Storage/Disconnect-ExportPoolWindow.png "Export Pool Window")

[Figure 3: Export Pool Window](#figure-3)](../../../../images/SCALE/Storage/Disconnect-ExportPoolWindow.png)

Leave **Delete saved configuration from TrueNAS?** option selected and then select the **Confirm Export Pool** option to activate the **Disconnect** button.

Click **Disconnect** to begin the export.

### Deleting a Pool

After backing up critical data stored in the pool you plan to export, click **Disconnect** for the pool.

Click **Delete Pool** in the \**Disconnect *poolname** window.

[![Delete Pool Window](../../../../images/SCALE/Storage/Diconnect-DeletePoolWindow.png "Delete Pool Window")

[Figure 4: Delete Pool Window](#figure-4)](../../../../images/SCALE/Storage/Diconnect-DeletePoolWindow.png)

To delete the pool and erase all the data on the pool, leave **Remove all releated configurations** selected, and then select **Confirm Delete Pool**.
Enter the pool name in the confirmation text field, to activate the **Disconnect** button.

Click **Disconnect** to delete the pool. A confirmation dialog opens when the delete operation completes.

## Upgrading a Pool

Upgrading a storage pool is typically not required unless the new OpenZFS feature flags are deemed necessary for required or improved system operation.

Do not do a pool-wide ZFS upgrade until you are ready to commit to this TrueNAS major version! You can not undo a pool upgrade, and you lose the ability to roll back to an earlier major version!

The **Upgrade** button displays on the **Storage Dashboard** for existing pools after an upgrade to a new TrueNAS major version that includes new [OpenZFS feature flags](../../../../scale/gettingstarted/versionnotes/#component-versions).
Newly created pools are always up to date with the OpenZFS feature flags available in the installed TrueNAS version.

[![Upgrade Pool Confirmation Dialog](../../../../images/SCALE/Storage/StorageDashboardUpgradPoolConfirmationDialog.png "Upgrade Pool Confirmation Dialog")

[Figure 5: Upgrade Pool Confirmation Dialog](#figure-5)](../../../../images/SCALE/Storage/StorageDashboardUpgradPoolConfirmationDialog.png)

Upgrading pools only takes a few seconds and is non-disruptive.
However, the best practice is to upgrade a pool while it is not in heavy use.
The upgrade process suspends I/O for a short period but is nearly instantaneous on a quiet pool.

It is not necessary to stop sharing services to upgrade the pool.

## Running a Pool Data Integrity Check (Scrub)

> A scrub is a data integrity check of your pool. Scrubs identify data integrity problems, detect silent data corruptions caused by transient hardware issues, and provide early disk failure alerts.

Use **Scrub Now** on the **Storage Health** pool widget to start a pool data integrity check.

[![Storage Health Widget](../../../../images/SCALE/Storage/StorageHealthWidget.png "Storage Health Widget")

[Figure 6: Storage Health Widget](#figure-6)](../../../../images/SCALE/Storage/StorageHealthWidget.png)

Click **Scrub Now** to open the **Scrub Pool** dialog, then click **Start Scrub** to begin the process.

If TrueNAS detects problems during the scrub operation, it corrects them or generates an [alert](../../../../scale/toptoolbar/alerts/) in the web interface.

### Scheduling Scrub Tasks

TrueNAS automatically creates a scheduled scrub for each pool that runs every Sunday at 12:00 AM.

The **Storage Health** widget shows the scheduled scrub status:

* **Scheduled Scrub: None Set** with a **Schedule** link if no scrub task exists
* **Scheduled Scrub: [when]** with a **Configure** link if a scrub task is configured and enabled

Click **Schedule** to create a new scrub schedule or **Configure** to modify an existing schedule. This opens the **Configure Scheduled Scrub** screen, where you can set the schedule, number of threshold days, and enable or disable the scheduled scrub.

**Threshold Days** sets the days before a completed scrub can run again.
This controls the task schedule.
For example, scheduling a scrub to run daily and setting threshold days to *7* means the scrub attempts to run daily.
When the scrub is successful, TrueNAS continues to check daily but does not run again until *seven* days have elapsed.
Using a multiple of *seven* ensures the scrub always occurs on the same weekday.

> Starting in TrueNAS 25.10, resilver priority settings are now located in **System Settings > Advanced Settings** on the **Storage** widget.

## Managing Pool Disks

The **Disks** button on the **Storage Dashboard** screen and the **View Disks** button on the **Disk Health** widget open the **Disks** screen.

**View VDEVs** on the **VDEVs** widget opens the ***Poolname* VDEVs** screen.
To manage disks in a pool, click on the VDEV to expand it and show the disks in that VDEV.
Click on a disk to see the widgets for that disk.
You can take a disk offline, detach it, replace it, manage the SED encryption password, and perform other disk management tasks from this screen.

See [Replacing Disks](../../../../scale/storage/disks/replacingdisks/) for more information on the **Offline**, **Replace** and **Online** options.

## Expanding a Pool

There are a few ways to increase the size of an existing pool:

* Add one or more drives to an existing RAIDZ VDEV.
* Add a new VDEV of the same type.
* Add a new VDEV of a different type.
* Replace all existing disks in the VDEV with larger disks.

Adding a new special VDEV increases usable space in combination with a special\_small\_files VDEV, but it is not encouraged.
A VDEV limits all disks to the usable capacity of the smallest attached device.

When you use one of the above methods, TrueNAS does not automatically expand the pool to fit newly available space.

[![Expand Pool Dialog](../../../../images/SCALE/Storage/ExpandPoolDialog.png "Expand Pool Dialog")

[Figure 7: Expand Pool Dialog](#figure-7)](../../../../images/SCALE/Storage/ExpandPoolDialog.png)

To expand an existing pool:

1. Navigate to **Storage**, click on the more\_vert dropdown menu, and select **Expand Pool**.
2. Select **Confirm** in the **Expand Pool** pop-up screen.
3. Click **Continue** to initiate the pool expansion process.

TrueNAS expands the pool to use the additional available capacity.

### Extending a RAIDZ VDEV

Extend a RAIDZ VDEV to add additional disks one at a time, expanding capacity incrementally.
This is useful for small pools (typically with only one RAID-Z VDEV), where there is not enough hardware capacity to add a second VDEV, doubling the number of disks.

Overview and Considerations

TrueNAS RAIDZ extensions to allow incremental expansion of an existing RAIDZ VDEV using one more disk.
RAIDZ extension allows resource- or hardware-limited home lab and small enterprise users to expand storage capacity with lower upfront costs compared to traditional ZFS expansion methods.

To expand a RAIDZ array, TrueNAS reads data from the current disks and rewrites it onto the new configuration, including any additional disks.

Data redundancy is maintained.
Make sure the pool is healthy before beginning the expansion process.
If a disk fails mid-expansion, the process pauses until the RAIDZ virtual device (vdev) is healthy again, typically by replacing the failed disk and waiting for the system to rebuild.

The storage pool remains accessible throughout the expansion.
If you restart or export/import the pool, the expansion resumes from where it left off.

After the expansion, the extra space becomes available for use.

The fault-tolerance level of the RAIDZ array remains unchanged.
For example, a four-disk-wide RAIDZ2 expanded to a six-disk-wide RAIDZ2 still cannot lose more than two disks at a time.

You can expand a RAIDZ vdev multiple times.

Existing data blocks retain their original data-to-parity ratio and block width, but are spread across the larger set of disks.
New data blocks adopt the new data-to-parity ratio and width.
Because of this overhead, an extended RAIDZ VDEV can report a lower total capacity than a freshly created VDEV with the same number of disks.

[![RAIDZ Expansion](../../../../images/Reference/RaidzExpansion.png "RAIDZ Expansion")

[Figure 8: RAIDZ Expansion](#figure-8)

Before (left) and after (right) expansion of a four-disk to five-disk RAIDZ1
Thanks to Matt Ahrens ([Source](https://arstechnica.com/gadgets/2021/06/raidz-expansion-code-lands-in-openzfs-master/))](../../../../images/Reference/RaidzExpansion.png)

Extended VDEVs recover lost headroom because existing data is read and rewritten to the new parity ratio.
This can occur naturally over the lifetime of the pool as you modify or delete data.
Replicate and rewrite the data to the extended pool to manually recover capacity.

You can use the [RAIDZ Extension Calculator](../../../../references/extensioncalculator/) to visualize potential lost headroom and capacity available to recover by rewriting existing data.

> While this process can recover the actual lost capacity, reported capacity continues to rely on the old data-to-parity ratio.
> An expanded vdev can continue to report a lower than expected capacity, even after rewriting old data to the new parity ratio.
> This accounting inconsistency does not impact the actual available capacity of the vdev.

For more information, read the [article written by Jim Salter](https://arstechnica.com/gadgets/2021/06/raidz-expansion-code-lands-in-openzfs-master/) at Ars Technica and the upstream [RAIDZ extension](https://github.com/openzfs/zfs/pull/15022) PR, sponsored by iXsystems, at OpenZFS.
See also [“ZFS RAIDZ Expansion Is Awesome but Has a Small Caveat”](https://louwrentius.com/zfs-raidz-expansion-is-awesome-but-has-a-small-caveat.html) by Louwrentius for an in-depth discussion of lost capacity and recovering overhead.

To extend a RAIDZ VDEV, go to **Storage**.
Locate the pool and click **View VDEVs** on the **VDEVs** widget to open the ***Poolname* VDEVs** screen.

[![Devices Screen](../../../../images/SCALE/Storage/DevicesMirrorVDEVSelected.png "Devices Screen")

[Figure 9: Devices Screen](#figure-9)](../../../../images/SCALE/Storage/DevicesMirrorVDEVSelected.png)

Select the target VDEV and click **Extend** to open the **Extend Vdev** window.

[![Extend Vdev](../../../../images/SCALE/Storage/ExtendVdev.png "Extend Vdev")

[Figure 10: Extend Vdev](#figure-10)](../../../../images/SCALE/Storage/ExtendVdev.png)

Select an available disk from the **New Disk** dropdown menu.
Click **Extend**.

A job progress window opens.
TrueNAS returns to the ***Poolname* VDEVs** screen when complete.

### Adding a VDEV to a Pool

ZFS supports adding VDEVs to an existing ZFS pool to increase the capacity or performance of the pool.
To extend a pool by mirroring, you must add a data VDEV of the same type as existing VDEVs.

> You cannot change the original encryption or data VDEV configuration.

Adding VDEV Examples

* To make a striped mirror, add the same number of drives to extend a ZFS mirror.
  For example, you start with ten available drives. Create a mirror of two drives, then extend the mirror by adding another mirror of two drives. Repeat this three more times until you add all ten drives.
* To make a stripe of two 3-drive RAIDZ1 VDEVs (similar to RAID 50 on a hardware controller), add another three drives as a new RAIDZ1 VDEV to the existing single 3-drive RAIDZ1 VDEV pool.
* To make a stripe of two 6-disk RAIDZ2 VDEVs (similar to RAID 60 on a hardware controller), add another six drives as a new RAIDZ2 VDEV to the existing single 6-drive RAIDZ2 VDEV pool.
* To add a deduplication VDEV, we suggest creating the VDEV when you first create the pool to ensure that all metadata or deduplication tables are stored on it.
  Special or deduplication VDEVs added to a pool with existing data are only populated with new writes.

To add a VDEV to an existing pool, you can:

* Click **Add To Pool** to open the **Add To Pool** window, and select **Existing Pool**. Select the pool on the **Existing Pool** dropdown.

  [![Add To Pool - Existing Pool](../../../../images/SCALE/Storage/AddToPoolExistingPoolWindow.png "Add To Pool - Existing Pool")

  [Figure 11: Add To Pool - Existing Pool](#figure-11)](../../../../images/SCALE/Storage/AddToPoolExistingPoolWindow.png)

or

* Click **View VDEVs** on the **VDEVs** widget to open the ***Poolname* VDEVs** screen, then click **Add VDEV** to open the **Add Vdevs to Pool** wizard.

  [![Add VDEVs to Pool Wizard](../../../../images/SCALE/Storage/AddVdevsToPoolScreen.png "Add VDEVs to Pool Wizard")

  [Figure 12: Add VDEVs to Pool Screen](#figure-12)](../../../../images/SCALE/Storage/AddVdevsToPoolScreen.png)

> ![](../../../../favicon/TN-favicon-32x32.png)
> TrueNAS Enterprise
>
> Enterprise systems that are licensed for and contain SEDs display a message about SED encryption, indicating that only SED-capable disks are available for VDEV selection within the SED-encrypted pool.
> Pools that are not SED encrypted do not display this message.

Adding a vdev to an existing pool follows the same process as documented in [Create Pool](../../../../scale/storage/pools/creatingpools/).

Click on the type of vdev you want to add. For example, to add a spare, click on **Spare** to show the vdev spare options.

[![Add VDEVs to Pool Spare Example](../../../../images/SCALE/Storage/AddVdevToPoolSpareScreen.png "Add VDEVs to Pool Spare Example")

[Figure 13: Add VDEVs to Pool Spare Example](#figure-13)](../../../../images/SCALE/Storage/AddVdevToPoolSpareScreen.png)

Select the layout, mirror, or stripe.

Select the disk size to use the **Automated Disk Selection** option. The **Width** and **Number of VDEVs** fields populate with default values based on the layout and disk size selected. To change this, select new values from the dropdown lists.

Adding a VDEV Manually

To add the vdev manually, click **Manual Disk Selection** to open the **Manual Selection** screen.

[![Add Vdev Manual Selection Screen](../../../../images/SCALE/Storage/AddVdevToPoolManualSelectionScreen.png "Add Vdev Manual Selection Screen")

[Figure 14: Add Vdev Manual Selection Screen](#figure-14)](../../../../images/SCALE/Storage/AddVdevToPoolManualSelectionScreen.png)

Click **Add** to show the vdev options available for the vdev type.
The example image shows adding a stripe vdev for the spare.
Vdev options are limited by the number of available disks in your system and the configuration of any existing vdevs of that type in the pool.
Drag the disk icon to the stripe vdev, then click **Save Selection**.

[![Add Disk to Stripe Vdev for Spare](../../../../images/SCALE/Storage/ManualSelectionAddVdevAddDisk.png "Add Disk to Stripe Vdev for Spare")

[Figure 15: Add Disk to Stripe Vdev for Spare](#figure-15)](../../../../images/SCALE/Storage/ManualSelectionAddVdevAddDisk.png)

The **Manual Selection** screen closes and returns to the **Add Vdev to Pool** wizard screen (in this case, the Spare option).

[![Add Vdev to Pool Spare with Vdev Added](../../../../images/SCALE/Storage/AddVdevToPoolSpareWithVdevAdded.png "Add Vdev to Pool Spare with Vdev Added")

[Figure 16: Add Vdev to Pool Spare with Vdev Added](#figure-16)](../../../../images/SCALE/Storage/AddVdevToPoolSpareWithVdevAdded.png)

You can accept the change or click **Edit Manual Disk Selection** to change the disk added to the strip vdev for the spare, or click **Reset Step** to clear the strip vdev from the spare completely.
Click either **Next** or a numbered item to add another type of vdev to this pool.

Repeat the same process above for each type of vdev to add.

Click **Save and Go to Review** to show the **Review** screen when ready to save your changes.

[![Add Vdev to Pool Review Screen](../../../../images/SCALE/Storage/AddVdevToPoolReviewScreen.png "Add Vdev to Pool Review Screen")

[Figure 17: Add Vdev to Pool Review Screen](#figure-17)](../../../../images/SCALE/Storage/AddVdevToPoolReviewScreen.png)

To make changes, click either **Back** or the vdev option (i.e., **Log**, **Cache**, etc.) to return to the settings for that vdev.
To clear all changes, click **Start Over**.
Select **Confirm**, then click **Start Over** to clear all changes.

Click **Update Pool** to save changes.

#### Adding a Deduplication VDEV

You can add a deduplication VDEV to an existing pool, but files in the pool might or might not have deduplication applied to them.
When adding a deduplication VDEV to an existing pool, any existing entries in the deduplication table remain on the data VDEVs until the data they reference is rewritten.

After adding a deduplication VDEV to a pool, and when adding duplicated files to the pool, the **Storage Health** widget on the **Storage Dashboard** shows two links, **Prune** and **Set Quota**. These links do not show if duplicated files do not exist in the pool.

Use **Prune** to set the parameters used to prune the deduplication table (DDT). When pruning the size, select the percentage or age measurement to use.

[![Prune Deduplication Table Dialog](../../../../images/SCALE/Storage/DedupPruneDialog.png "Prune Deduplication Table Dialog")

[Figure 18: Prune Deduplication Table Dialog](#figure-18)](../../../../images/SCALE/Storage/DedupPruneDialog.png)

Use **Set Quota** to set the DDT quota. This determines the maximum table size allowed.
The default setting, **Auto**, allows the system to determine the quota based on the size of a dedicated dedup vdev when setting the quota limit.
This property works for both legacy and fast dedup tables.

[![Deduplication Quota Dialog](../../../../images/SCALE/Storage/DedupQutoaDialog.png "Deduplication Quota Dialog")

[Figure 19: Deduplication Quota Dialog](#figure-19)](../../../../images/SCALE/Storage/DedupQutoaDialog.png)

Change to **Custom** to set the quota to your preference.

Click **Save** to save and close the dialogs.

### Replacing Disks to Expand a Pool

To expand a pool by replacing disks with a higher-capacity disk, follow the same procedure as in [Replacing Disks](../../../../scale/storage/disks/replacingdisks/).

Insert a new disk into an empty enclosure slot. Remove the old disk only after completing the replacement operation.
If an empty slot is unavailable, you can off-line the existing disk and replace it in the same slot, but this reduces redundancy during the process.

Go to the **Storage Dashboard** and click **View VDEVs** on the **VDEVs** widget opens the ***Poolname* VDEVs** screen.

1. Click anywhere on the VDEV to expand it and select one of the existing disks.
2. (Optional) If replacing disks in the same slot, take one existing disk offline.

   [![Devices Disk Widgets](../../../../images/SCALE/Storage/DevicesDiskWidgets.png "Devices Disk Widgets")

   [Figure 20: Devices Disk Widgets](#figure-20)](../../../../images/SCALE/Storage/DevicesDiskWidgets.png)

   Click **Offline** on the **ZFS Info** widget to take the disk offline. The button toggles to **Online**.

   Remove the disk from the system.
3. Insert a larger capacity disk into an open enclosure slot (or if no empty slots, the slot of the offline disk being replaced).

   [![Replace and Online a Disk](../../../../images/SCALE/Storage/ReplaceDiskAndOnline.png "Replace and Online a Disk")

   [Figure 21: Replace and Online a Disk](#figure-21)](../../../../images/SCALE/Storage/ReplaceDiskAndOnline.png)

   a. Click **Replace** on the **Disk Info** widget on the ***Poolname* Devices** screen for the disk you off-lined.

   b. Select the new drive from the **Member Disk** dropdown list on the **Replacing disk *diskname*** dialog.

   [![Replacing Disk Dialog](../../../../images/SCALE/Storage/ReplacingDiskDialog.png "Replacing Disk Dialog")

   [Figure 22: Replacing Disk Dialog](#figure-22)](../../../../images/SCALE/Storage/ReplacingDiskDialog.png)
4. Add the new disk to the existing VDEV. Click **Replace Disk** to add the new disk to the VDEV and bring it online.

   Disk replacement fails when the selected disk has partitions or data present.
   To destroy any data on the replacement disk and allow the replacement to continue, select the **Force** option.

   [![Replacing Disk Status](../../../../images/SCALE/Storage/ReplacingDiskStatusDialog.png "Replacing Disk Status")

   [Figure 23: Replacing Disk Status](#figure-23)](../../../../images/SCALE/Storage/ReplacingDiskStatusDialog.png)

   After the disk wipe completes, TrueNAS starts replacing the failed disk.
   TrueNAS resilvers the pool during the replacement process.
   This can take a long time for pools with large amounts of data.
   When the resilver process completes, the pool status returns to **Online** status on the ***Poolname* Devices** screen.

Wait for the resilver to complete before replacing the next disk.
Repeat steps 1-4 for all attached disks.

After replacing the last attached disk, click **Expand** on the **Storage Dashboard** to increase the pool size to fit all available disk space.

## Removing VDEVs

You can always remove the L2ARC (cache) and SLOG (log) VDEVs from an existing pool, regardless of topology or VDEV type.
Removing these devices does not impact data integrity but can significantly impact read and write performance.

In addition, you can remove a data VDEV from an existing pool under specific circumstances.
This process preserves data integrity but has multiple requirements:

* Upgrade the pool with the `device_removal` zfs feature flag.

  The pool must be upgraded to a ZFS version with the `device_removal` feature flag.
  The system shows the [**Upgrade** button](#upgrading-a-pool) after upgrading TrueNAS when new ZFS feature flags are available.
* Use mirror or stripe VDEVs.

  All top-level VDEVs in the pool must be *only* mirrors or stripes.
* Keep special VDEVs in RAIDz data VDEVs.

  Special VDEVs cannot be removed when RAIDZ data VDEVs are present.
* Use the same basic allocation unit size.

  All top-level VDEVs in the pool must use the same basic allocation unit size (`ashift`).
* Maintain sufficient free space in the data VDEV for removed data.

  The remaining data VDEVs must contain sufficient free space to hold all data from the removed VDEV.

It is generally not possible to remove a device when a RAIDZ data VDEV is present.

To remove a VDEV from a pool:

1. Click \***View VDEVs** on the **VDEVs** widget opens the ***Poolname* VDEVs** screen.
2. Click the device or drive to remove, then click the **Remove** button in the **ZFS Info** widget.
   If the **Remove** button is not visible, check that all conditions for VDEV removal listed above are correct.
3. Confirm the removal operation and click the **Remove** button.

The VDEV removal process status shows in the [**Jobs** screen](../../../../scale/toptoolbar/jobsscreens/) (or alternately with the `zpool status` command).
Avoid physically removing or attempting to wipe the disks until the removal operation completes.

---

## Related Content

**Tutorial**

* [Adding and Managing Datasets](../../../../scale/datasets/managingdatasets/)
* [Configuring Advanced Settings](../../../../scale/systemsettings/advanced/advancedsettings/)
* [Creating Snapshots](../../../../scale/datasets/snapshots/creatingsnapshots/)
* [Import Pool](../../../../scale/storage/pools/importpool/)
* [Replacing Disks](../../../../scale/storage/disks/replacingdisks/)

**Getting Started**

* [TrueNAS Hardware Guide](../../../../scale/gettingstarted/tnhardwareguide/)
* [Setting Up Storage](../../../../scale/gettingstarted/configure/setupstoragescale/)

**Reference**

* [Storage Dashboard Screens](../../../../scale/storage/storagedashboardscreens/)
* [Disks Screen](../../../../scale/storage/disks/disksscreen/)
* [Encryption Screen](../../../../scale/datasets/encryption/encryptionscreen/)
* [Pool Creation Wizard Screen](../../../../scale/storage/pools/poolcreationwizardscreen/)
* [Snapshots Screens](../../../../scale/datasets/snapshots/snapshotsscreens/)

**General Reference**

* [Bits or Bytes?](../../../../references/bitsorbytes/)
* [ZFS Deduplication](../../../../references/zfsdeduplication/)
* [ZFS Primer](../../../../references/zfsprimer/)
* [ZFS dRAID Primer](../../../../references/draidprimer/)
* [ZFS ZIL and SLOG](../../../../references/zilandslog/)

**Have more questions?**

For further discussion or assistance, see these resources:

Found content that needs an update?
You can
directly! To request changes to this content, click the **Feedback** button located on the middle-right side of the page (might require disabling ad blocking plugins).