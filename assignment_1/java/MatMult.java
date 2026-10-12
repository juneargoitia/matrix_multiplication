import java.io.EOFException;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.Locale;

public class MatMul {

    static void matmul(double[] a, double[] b, double[] c, int n) {
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                double sum = 0.0;
                for (int k = 0; k < n; k++) {
                    sum += a[i * n + k] * b[k * n + j];
                }
                c[i * n + j] = sum;
            }
        }
    }

    static void readMatrix(String path, double[] dst) throws IOException {
        try (FileChannel ch = FileChannel.open(Paths.get(path), StandardOpenOption.READ)) {
            long expected = (long) dst.length * 8L;
            if (ch.size() != expected) {
                throw new IOException(path + ": expected " + expected + " bytes, found " + ch.size());
            }
            ByteBuffer buf = ByteBuffer.allocate(1 << 20).order(ByteOrder.LITTLE_ENDIAN);
            int pos = 0;
            while (pos < dst.length) {
                int cnt = Math.min(buf.capacity() / 8, dst.length - pos);
                buf.clear();
                buf.limit(cnt * 8);
                while (buf.hasRemaining()) {
                    if (ch.read(buf) < 0) throw new EOFException(path);
                }
                buf.flip();
                buf.asDoubleBuffer().get(dst, pos, cnt);
                pos += cnt;
            }
        }
    }

    static void writeMatrix(String path, double[] src) throws IOException {
        try (FileChannel ch = FileChannel.open(Paths.get(path), StandardOpenOption.WRITE,
                StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING)) {
            ByteBuffer buf = ByteBuffer.allocate(1 << 20).order(ByteOrder.LITTLE_ENDIAN);
            int pos = 0;
            while (pos < src.length) {
                int cnt = Math.min(buf.capacity() / 8, src.length - pos);
                buf.clear();
                buf.asDoubleBuffer().put(src, pos, cnt);
                buf.limit(cnt * 8);
                while (buf.hasRemaining()) ch.write(buf);
                pos += cnt;
            }
        }
    }

    static void emit(String line) {
        System.out.println(line);
        System.out.flush();
    }

    public static void main(String[] args) throws IOException {
        if (args.length != 5 && args.length != 6) {
            System.err.println("usage: java MatMul A.bin B.bin n warmup reps [out.bin]");
            System.exit(2);
        }
        int n = Integer.parseInt(args[2]);
        int warmup = Integer.parseInt(args[3]);
        int reps = Integer.parseInt(args[4]);
        if (n < 1 || warmup < 0 || reps < 1) {
            System.err.println("invalid n/warmup/reps");
            System.exit(2);
        }
        long count = (long) n * n;
        if (count > Integer.MAX_VALUE - 8) {
            System.err.println("n too large for a single Java array");
            System.exit(3);
        }

        double[] a = new double[(int) count];
        double[] b = new double[(int) count];
        double[] c = new double[(int) count];
        readMatrix(args[0], a);
        readMatrix(args[1], b);

        Runtime rt = Runtime.getRuntime();
        System.gc();
        long heapAfterAlloc = rt.totalMemory() - rt.freeMemory();

        emit("INFO,lang,java");
        emit("INFO,java_version," + System.getProperty("java.version") + " "
                + System.getProperty("java.vm.name") + " (" + System.getProperty("java.vendor") + ")");
        emit("INFO,n," + n);
        emit("HEAP_USED_AFTER_ALLOC," + heapAfterAlloc);

        for (int w = 0; w < warmup; w++) {
            long t0 = System.nanoTime();
            matmul(a, b, c, n);
            long t1 = System.nanoTime();
            emit(String.format(Locale.ROOT, "WARMUP,%d,%.9f", w, (t1 - t0) * 1e-9));
        }
        for (int r = 0; r < reps; r++) {
            long t0 = System.nanoTime();
            matmul(a, b, c, n);
            long t1 = System.nanoTime();
            emit(String.format(Locale.ROOT, "REP,%d,%.9f", r, (t1 - t0) * 1e-9));
        }

        double checksum = 0.0;
        for (int i = 0; i < c.length; i++) checksum += c[i];
        emit("CHECKSUM," + Double.toString(checksum));

        if (args.length == 6) writeMatrix(args[5], c);

        if (System.getenv("MATMUL_HOLD") != null) {
            emit("DONE");
            while (System.in.read() != -1) { }
        }
    }
}
