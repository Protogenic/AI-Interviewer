import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const journalists = [
  {
    id: 'dud',
    name: 'Юрий Дудь',
    description:
      'Прямолинейный и дерзкий стиль: острые личные вопросы, факты из прошлого, неудобные темы без намеков.',
  },
  {
    id: 'sobchak',
    name: 'Ксения Собчак',
    description:
      'Провокационный и светский стиль: скандальные детали, светские темы, личная жизнь и эпатажные вопросы.',
  },
  {
    id: 'pozner',
    name: 'Владимир Познер',
    description:
      'Интеллигентный и глубокий стиль: философские вопросы, долгие паузы, поиск противоречий в словах собеседника.',
  },
];

async function main() {
  for (const journalist of journalists) {
    await prisma.journalist.upsert({
      where: { id: journalist.id },
      update: { name: journalist.name, description: journalist.description },
      create: journalist,
    });
  }
  console.log('Seed complete: 3 journalists inserted/updated');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
