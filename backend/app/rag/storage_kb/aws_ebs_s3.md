[View a markdown version of this page](EBSFeatures.md)

Features and benefits of Amazon EBS volumes - Amazon EBS

[Documentation](/index.html)[Amazon EBS](/ebs/index.html)[User Guide](what-is-ebs.html)

[Data availability](#availability-benefit)[Data persistence](#persistence-benefit)[Data encryption](#encryption-benefit)[Data security](#security-benefit)[Snapshots](#backup-benefit)[Flexibility](#flexibility-benefit)

# Features and benefits of Amazon EBS volumes

EBS volumes provide benefits that are not provided by instance store volumes.

###### Benefits

* [Data availability](#availability-benefit)
* [Data persistence](#persistence-benefit)
* [Data encryption](#encryption-benefit)
* [Data security](#security-benefit)
* [Snapshots](#backup-benefit)
* [Flexibility](#flexibility-benefit)

## Data availability

When you create an EBS volume, it is automatically replicated within its Availability
Zone to prevent data loss due to failure of any single hardware component. You can attach an
EBS volume to any EC2 instance in the same Availability Zone. After you attach a volume, it
appears as a native block device similar to a hard drive or other physical device. At that
point, the instance can interact with the volume just as it would with a local drive. You
can connect to the instance and format the EBS volume with a file system, such as `Ext4`
for a Linux instance or `NTFS` for a Windows instance, and then install
applications.

If you attach multiple volumes to a device that you have named, you can stripe data
across the volumes for increased I/O and throughput performance.

You can attach `io1` and `io2` EBS volumes to up to 16 Nitro-based instances.
For more information, see [Attach an EBS volume to multiple EC2 instances using Multi-Attach](./ebs-volumes-multi.html).
Otherwise, you can attach an EBS volume to a single instance.

You can get monitoring data for your EBS volumes, including root device volumes for
EBS-backed instances, at no additional charge. For more information about monitoring
metrics, see [Amazon CloudWatch metrics for Amazon EBS](./using_cloudwatch_ebs.html).
For information about tracking the status of your volumes, see [Amazon EventBridge events for Amazon EBS](./ebs-cloud-watch-events.html).

## Data persistence

An EBS volume is off-instance storage that can persist independently from the life of an
instance. You continue to pay for the volume usage as long as the data persists.

EBS volumes that are attached to a running instance can automatically detach from the
instance with their data intact when the instance is terminated if you uncheck the
**Delete on Termination** check box when you configure EBS volumes for
your instance on the EC2 console. The volume can then be reattached to a new instance,
enabling quick recovery. If the check box for **Delete on Termination** is
checked, the volume(s) will delete upon termination of the EC2 instance. If you are using an
EBS-backed instance, you can stop and restart that instance without affecting the data
stored in the attached volume. The volume remains attached throughout the stop-start cycle.
This enables you to process and store the data on your volume indefinitely, only using the
processing and storage resources when required. The data persists on the volume until the
volume is deleted explicitly. The physical block storage used by deleted EBS volumes is
overwritten with zeroes or cryptographically pseudorandom data before it is allocated to a
new volume. If you are dealing with sensitive data, you should consider encrypting your
data manually or storing the data on a volume protected by Amazon EBS encryption. For more information,
see [Amazon EBS encryption](./ebs-encryption.html).

By default, the root EBS volume that is created and attached to an instance at launch is
deleted when that instance is terminated. You can modify this behavior by changing the value
of the flag `DeleteOnTermination` to `false` when you launch the
instance. This modified value causes the volume to persist even after the instance is
terminated, and enables you to attach the volume to another instance.

By default, additional EBS volumes that are created and attached to an instance at
launch are not deleted when that instance is terminated. You can modify this behavior by
changing the value of the flag `DeleteOnTermination` to `true` when
you launch the instance. This modified value causes the volumes to be deleted when the
instance is terminated.

## Data encryption

For simplified data encryption, you can create encrypted EBS volumes with the
Amazon EBS encryption feature. All EBS volume types support encryption. You can use encrypted EBS
volumes to meet a wide range of data-at-rest encryption requirements for regulated/audited
data and applications. Amazon EBS encryption uses 256-bit Advanced Encryption Standard algorithms
(AES-256) and an Amazon-managed key infrastructure. The encryption occurs on the server that
hosts the EC2 instance, providing encryption of data-in-transit from the EC2 instance to
Amazon EBS storage. For more information, see [Amazon EBS encryption](./ebs-encryption.html).

Amazon EBS encryption uses AWS KMS keys when creating encrypted volumes and any snapshots
created from your encrypted volumes. The first time you create an encrypted EBS volume in
a Region, a default AWS managed KMS key is created for you automatically. This key is
used for Amazon EBS encryption unless you create and use a customer managed key. Creating your own customer managed key
gives you more flexibility, including the ability to create, rotate, disable, define access
controls, and audit the encryption keys used to protect your data. For more information,
see the [AWS Key Management Service Developer Guide](https://docs.aws.amazon.com/kms/latest/developerguide/).

## Data security

Amazon EBS volumes are presented to you as raw, unformatted block devices. These
devices are logical devices that are created on the EBS infrastructure and the Amazon EBS service ensures that the
devices are logically empty (that is, the raw blocks are zeroed or they contain cryptographically pseudorandom
data) prior to any use or re-use by a customer.

If you have procedures that require that all data
be erased using a specific method, either after or before use (or both), such as those detailed in **DoD 5220.22-M** (National Industrial Security Program Operating Manual) or **NIST 800-88** (Guidelines for Media Sanitization), you have the ability to do so on Amazon EBS.
That block-level activity will be reflected down to the underlying storage media within the Amazon EBS service.

## Snapshots

Amazon EBS provides the ability to create snapshots (backups) of any EBS volume and write a
copy of the data in the volume to Amazon S3, where it is stored redundantly in multiple
Availability Zones. The volume does not need to be attached to a running instance in order
to take a snapshot. As you continue to write data to a volume, you can periodically create a
snapshot of the volume to use as a baseline for new volumes. These snapshots can be used to
create multiple new EBS volumes or move volumes across Availability Zones. Snapshots of
encrypted EBS volumes are automatically encrypted.

When you create a new volume from a snapshot, it's an exact copy of the original volume
at the time the snapshot was taken. EBS volumes that are created from encrypted snapshots are
automatically encrypted. By optionally specifying a different Availability Zone, you can use
this functionality to create a duplicate volume in that zone. The snapshots can be shared with
specific AWS accounts or made public. When you create snapshots, you incur charges in Amazon S3
based on the size of the data being backed up, not the size of the source volume. Subsequent
snapshots of the same volume are incremental snapshots. They include only changed and new data
written to the volume since the last snapshot was created, and you are charged only for this
changed and new data.

Snapshots are incremental backups, meaning that only the blocks on the volume that have
changed after your most recent snapshot are saved. If you have a volume with 100 GiB of
data, but only 5 GiB of data have changed since your last snapshot, only the 5 GiB of
modified data is written to Amazon S3. Even though snapshots are saved incrementally, the
snapshot deletion process is designed so that you need to retain only the most recent
snapshot.

To help categorize and manage your volumes and snapshots, you can tag them with metadata
of your choice.

To back up your volumes automatically, you can use [Amazon Data Lifecycle Manager](./snapshot-lifecycle.html) or [AWS Backup](https://docs.aws.amazon.com/aws-backup/latest/devguide/).

## Flexibility

EBS volumes support live configuration changes while in production. You can modify
volume type, volume size, and IOPS capacity without service interruptions. For more
information, see [Modify an Amazon EBS volume using Elastic Volumes operations](./ebs-modify-volume.html).

![Warning](https://d1ge0kk1l5kms0.cloudfront.net/images/G/01/webservices/console/warning.png) **Javascript is disabled or is unavailable in your browser.**

To use the Amazon Web Services Documentation, Javascript must be enabled. Please refer to your browser's Help pages for instructions.

[Document Conventions](/general/latest/gr/docconventions.html)

EBS volumes

EBS volume types

Did this page help you? - Yes

Thanks for letting us know we're doing a good job!

If you've got a moment, please tell us what we did right so we can do more of it.

Did this page help you? - No

Thanks for letting us know this page needs work. We're sorry we let you down.

If you've got a moment, please tell us how we can make the documentation better.