import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';
import Link from '@docusaurus/Link';

type FeatureItem = {
  title: string;
  imageAddress: string;
  description: JSX.Element;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'مستندات برنامه درسی علوم داده',
    imageAddress: 'img/Data_Science.png',
    description: (
      <Link to='/docs'>مستندات برنامه درسی علوم داده</Link>
    ),
  },
  {
    title: 'برنامه درسی',
    imageAddress: 'img/DS-Word-Cloud.png',
    description: (
      <Link to='/docs/category/curriculum'>
        برنامه درسی پیشنهادی کارشناسی علوم داده
      </Link>
    ),
  },
  {
    title: 'جداول خلاصه',
    imageAddress: 'img/base.png',
    description: (
      <Link to='/docs/summary-tables'>جداول طبقه‌بندی شده درس‌ها</Link>
    ),
  },
];

function Feature({ title, imageAddress, description }: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className='text--center'>
        <img className={styles.featureImg} src={imageAddress} />
      </div>
      <div className='text--center padding-horiz--md'>
        <Heading as='h3'>{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): JSX.Element {
  return (
    <section className={styles.features}>
      <div className='container'>
        <div className='row'>
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
